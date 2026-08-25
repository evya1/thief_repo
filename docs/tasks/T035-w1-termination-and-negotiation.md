---
id: T035
status: done
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
gates: []
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

- Sub-game termination follows the production contract: a subgame
  whose configured `max_moves` and `survival_threshold` diverge refuses to start; a
  move-cap exhaustion below the survival threshold refuses to score rather than guessing
  an outcome.
- Per-subgame negotiation (arena/word cap/scent-model lock) is re-validated at the start
  of every sub-game, not only once per series.

## Constraints

- Incompatible termination values are rejected before play.
- Do not touch `common/transport/negotiate.py` or `common/transport/audit.py` here — those
  are `T036`'s (W2) scope.
- The planning-graph overlap and cross-repository parity checks are resolved.

## Acceptance criteria

- [x] `max_moves != survival_threshold` at subgame start is refused with a typed error, not a silent clamp.
- [x] Incompatible termination values cannot produce a guessed CAPTURE or SURVIVE outcome.
- [x] Per-subgame negotiation re-runs and is covered by a test that changes terms between subgames.
- [x] Police/Thief shared behavior passes byte-parity verification.

## Verification

- `uv run pytest tests/unit/wire tests/integration/test_series_loopback.py`
- `uv run python scripts/check_planning_graph.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and
newly discovered work, including the exact source SHA police_repo must match.

## Result and evidence

Complete. The full unit/integration suites and cross-repository parity gate verify the shared
termination and per-subgame negotiation behavior.
