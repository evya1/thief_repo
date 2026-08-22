---
id: T035
status: blocked
priority: P0
task_type: component
component: C01
optional: false
implements:
  - ARCH-002
  - ARCH-003
context_files:
  - docs/spec/OPEN_QUESTIONS.md
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - common/transport/subgame.py
read_set:
  - src/thief_peer/wire/session.py
depends_on:
  - T004
  - T010
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
  - id: OPEN-011
    kind: decision
    scope: termination
    blocks: criterion
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/subgame.py
  - src/thief_peer/wire/session.py
  - tests/unit/wire/
  - tests/integration/test_series_loopback.py
risk: medium
---

# T035 — Wave W1: Termination and Per-Subgame Negotiation (thief_repo)

## Purpose

Close remaining termination-handling and per-subgame negotiation gaps identified in the
governance/task-preparation pass of 2026-08-22. `thief_repo` is the **source-of-truth
repository** for this wave's `common/transport/subgame.py` edits; `police_repo` runs the
required byte-parity check task (its own `T035`) against the exact patch landed here.

## Expected outcome

- Sub-game termination follows the `OPEN-011` operational convention exactly: a sub-game
  whose configured `max_moves` and `survival_threshold` diverge refuses to start; a
  move-cap exhaustion below the survival threshold refuses to score rather than guessing
  an outcome.
- Per-subgame negotiation (arena/word cap/scent-model lock) is re-validated at the start
  of every sub-game, not only once per series.

## Constraints

- `OPEN-011` stays **officially open**. Do not convert the convention into a claimed
  official resolution anywhere in code comments, docs, or task evidence.
- Do not touch `common/transport/negotiate.py` or `common/transport/audit.py` here — those
  are `T036`'s (W2) scope.
- This task cannot be claimed (`blocks: start`) until the planning-graph overlap between
  `T009` and `T030` on `common/transport/series.py` is resolved by the orchestrator (see
  `T040`/W6), because `T009`'s negotiation work and this task's termination work both
  touch subgame-lifecycle shared code and must not run concurrently unreconciled.

## Acceptance criteria

- [ ] `max_moves != survival_threshold` at sub-game start is refused with a typed error, not a silent clamp.
- [ ] Move-cap exhaustion below `survival_threshold` produces an unresolved/refused result, never a guessed CAPTURE or SURVIVE outcome.
- [ ] Per-subgame negotiation re-runs (not cached from series start) and is covered by a test that changes terms between sub-games within one series.
- [ ] `police_repo`'s `T035` byte-parity check passes against this task's `common/transport/subgame.py` diff.

## Verification

- `uv run pytest tests/unit/wire tests/integration/test_series_loopback.py`
- `uv run python scripts/check_planning_graph.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and
newly discovered work, including the exact source SHA police_repo must match.

## Result and evidence
