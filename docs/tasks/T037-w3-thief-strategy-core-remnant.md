---
id: T037
status: ready
priority: P1
task_type: component
component: C02
optional: false
implements:
  - ARCH-007
  - STRAT-007
  - STRAT-008
  - STRAT-009
context_files:
  - docs/mechanisms/M-04-thief-strategy.md
  - docs/decisions/ADR-006-strategy-heuristic-priorities.md
read_set:
  - src/thief_peer/strategy/scoring.py
  - src/thief_peer/strategy/thief.py
depends_on:
  - T007
gates:
  - id: PLANQ-008
    kind: decision
    scope: heuristics
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - tests/unit/strategy/
  - tests/property/strategy/
risk: low
---

# T037 — Wave W3a: Thief Strategy Core — Remaining Gaps Only (thief_repo)

## Scope note (why this task is narrow)

`evya1/thief_repo#36` (merged into `thief-strategy`, base `f506bd8`, head `5c300bb`) already
landed: a pure scoring core (`strategy/scoring.py`, `select_thief_action` as testable data
in/out, `ThiefWeights` dataclass), explicit `orthogonal_mobility`/`destination` computation,
wire-boundary evidence normalization (`wire/evidence.py`, H3), and a documented finding that
the FR-T3 trap TERM is structurally unobservable on reachable non-terminal states (domain
physics gap, not a scoring bug). **This task does not redo that work.** Its only remaining
scope is verifying and closing the `ADR-006` gap: does the already-landed scoring order match
the approved Thief hard-constraint priority list, and do the two required negative-control
scenarios exist.

## Expected outcome

- `select_thief_action`'s constraint order is audited against `ADR-006`'s Thief ordering
  (legal-only → never-barrier(N/A) → avoid-confident-Police-cell → avoid-trapped → then
  distance/mobility/unvisited). Any mismatch is reported as a finding, not silently patched
  outside this task's write set.
- The always-STAY and disconnected-belief negative controls required by `ADR-006` exist as
  seeded, reproducible tests.

## Constraints

- Do not edit `src/thief_peer/strategy/` — if the audit finds the priority order genuinely
  wrong, that is new discovered work requiring its own task per AGENTS.md §"Newly discovered
  work gets a new task"; this task only adds tests and reports.
- Do not touch `wire/evidence.py`, `sdk.py`, or `wire/session.py` — those are settled by PR #36.

## Acceptance criteria

- [ ] A written audit note (in this task's Result section) confirms or refutes that `select_thief_action`'s effective ordering matches `ADR-006`.
- [ ] Always-STAY negative control exists and passes with the documented expected outcome.
- [ ] Disconnected-belief negative control exists and passes with the documented expected outcome.
- [ ] `T007`'s `heuristics`-scoped acceptance criterion can be closed on the strength of this evidence.

## Verification

- `uv run pytest tests/unit/strategy tests/property/strategy`

## Handoff contract

Report files changed, tests executed, exact results, the audit finding (match/mismatch with
`ADR-006`), decisions, deviations, blockers, newly discovered work.

## Result and evidence
