---
id: T042
status: done
priority: P0
task_type: component
component: C03
optional: false
implements:
  - ARCH-002
  - ARCH-003
  - NET-001
  - GAME-009
  - SEC-007
context_files:
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - docs/decisions/ADR-007-cross-role-strategy-port.md
  - common/transport/validators.py
  - common/transport/subgame.py
  - src/thief_peer/wire/session.py
read_set:
  - src/thief_peer/wire/brain.py
  - src/thief_peer/strategy/scoring.py
depends_on:
  - T036
gates: []
parallel_safe: false
claimed_by: orchestrator
claim_expires_at:
write_set:
  - common/transport/validators.py
  - common/transport/subgame.py
  - common/transport/turnseal.py
  - common/transport/turnfeed.py
  - src/thief_peer/wire/brain.py
  - src/thief_peer/wire/session.py
  - src/thief_peer/wire/capture_exchange.py
  - config/game.toml.example
  - tests/unit/transport/
  - tests/unit/wire/
  - tests/integration/test_playable_lifecycle.py
  - tests/integration/test_strategy_selfplay_kpi.py
  - tests/integration/test_strategy_selfplay_kpi_harness.py
risk: medium
---

# T042 — Review remediation: hostile-turn atomicity and opposite-role capture (thief_repo)

Closes the `thief_repo` half of the independent review dated 2026-08-22. `thief_repo` is
source-of-truth for the shared `common/transport/{validators,subgame,turnseal}.py` edits in
this wave (ADR-005); `police_repo` ports them byte-for-byte and runs the parity check in its
own `T044`.

Scope is exactly the review's findings. It does **not** reopen OPEN-011 termination
semantics, group scoring, reporting, GUI, or branch hygiene, and it does **not** change
ADR-007: no sibling policy is imported, copied, or wired into production move selection.

## Findings closed

| Finding | Fix | Evidence |
|---|---|---|
| HIGH-2 — hostile optional turn data passed validation and could mutate state before failing | `validate_turn(data, *, board_size)` is a pure function of the message plus the negotiated board size; the semantic preflight runs before the first mutation on both the wire and engine paths | `tests/unit/transport/test_turn_validation_general.py`, `tests/unit/wire/test_hostile_turn_atomicity.py` |
| MEDIUM-8 — a `thief_repo` peer assigned POLICE could not declare a capture at all | `barrier_placed` / `capture_claim` emission moved into the shared runtime session via `wire/capture_exchange.py` | `tests/unit/wire/test_capture_exchange.py`, `tests/integration/test_playable_lifecycle.py` |
| LOW-11 (thief half) — KPI/config wording overstated what was measured | KPI thief config now comes from `create_peer`'s production composition; `config/game.toml.example` documents the shipped `trap_risk(mobility <= 1)` predicate | `tests/integration/test_strategy_selfplay_kpi_harness.py`, `config/game.toml.example` |
| Sub-game boundary leak (found by the real two-process run during this wave, not by the review) | `play_subgame` reconciles the boundary: only a step-1 message can belong to the new sub-game, so the settling peer's owed final STAY (rule 35) is dropped instead of poisoning the fresh reorder window | `tests/unit/wire/test_hostile_turn_atomicity.py` boundary cases; the cross-repo series below |
| `w_trap` reachability (carried from the previous review) | verification only — the shipped predicate is already the reachable one-exit rule; `Board.boxed_in` is untouched | `tests/unit/strategy/test_scoring.py`, `tests/property/strategy/test_thief_prop.py` |

## Acceptance criteria

- `validate_turn` refuses a non-mapping message, an unknown sender, an out-of-bounds or
  malformed coordinate, a malformed `claim_response` / `win_claim`, and an extension field
  carrying a bare coordinate — each as a verdict, never as an uncaught exception.
- Bounds come from the negotiated `board_size`, never a hard-coded 7. An invalid
  `board_size` argument stays a programmer error and raises.
- On every refusal the inbox (`played`, `buffered`, `next_step`, `absorbed`), the applied
  window, the board/session, and the belief snapshot are unchanged.
- A POLICE-role sub-game declares `capture_claim` at the post-action cell on every
  non-barrier action including a legal STAY; a barrier turn declares `barrier_placed` and no
  capture claim; a crafted alternating-role game settles CAPTURE with agreeing audits.
- `common/` stays byte-identical to `police_repo`.
- ADR-007 unchanged; `T041` remains evaluation-only.

## Result

- `common/transport/turnseal.py` was extracted from `subgame.py`, and
  `src/thief_peer/wire/capture_exchange.py` from `wire/session.py`, so both files return
  under the 150-logical-line cap.
- Evidence SHAs are recorded in `docs/TODO_thief_strategy.md`.

## Two-process cross-repo evidence

`police_peer` (from `police_repo`) and `thief_peer` (from this repository) run as two
separate OS processes over FastMCP on localhost, six sub-games, artifacts written by each
side independently:

| | baseline at the audit anchors | after this wave |
|---|---|---|
| exit codes | 0 / 0 | 0 / 0 |
| `game_uid` match | yes | yes |
| `audit_ok` | 12/12 true | 12/12 true |
| captures | **0** — every sub-game ran to the 35-step ceiling | **3** |
| captures while *this* repository played POLICE | 0 | 0 — the SD-T7 stand-in selector never pursues; structural reachability is proved by the crafted alternating-role test instead |
| captures while `police_repo` played POLICE | 0 | 3 |

The zero-capture baseline is why the boundary leak was latent at the reviewed heads: no
sub-game ever ended early there, so no peer ever owed an unread final STAY.

`Session termination failed` (LOW-10) did **not** reproduce on a clean run. It appears only
alongside a crash, and its source is the dependency
`mcp/client/streamable_http.py:593` (`logger.warning`), emitted when the client tears down a
session whose peer process has already exited. No source-owned cause exists and no output is
suppressed.
