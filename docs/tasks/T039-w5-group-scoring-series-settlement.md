---
id: T039
status: blocked
priority: P1
task_type: component
component: C01
optional: false
implements:
  - ARCH-002
context_files:
  - docs/PRD.md
  - docs/spec/OPEN_QUESTIONS.md
read_set:
  - src/thief_peer/league/series.py
  - src/thief_peer/league/scoring.py
depends_on:
  - T019
  - T035
  - T036
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/league/series.py
  - src/thief_peer/league/scoring.py
  - common/transport/series.py
  - tests/unit/league/
risk: medium
---

# T039 — Wave W5: Group-Based Scoring and Series Settlement (thief_repo)

`thief_repo` is source-of-truth for the shared `common/transport/series.py` edits in this
wave; `police_repo` runs the byte-parity check in its own `T039`. This task cannot be
claimed until the planning-graph-reported overlap between `T009` and `T030` on
`common/transport/series.py` is reconciled (see `T040`/W6) — two tasks concurrently owning
edits to the same file is exactly the failure mode the checker exists to catch.

## Expected outcome

- Series-level settlement correctly aggregates group/pool results (not just head-to-head),
  per the project's league/reporting design in `docs/components/C06-reporting-league/`.
- Settlement respects the `production termination guard` convention: it never silently scores an incompatible
  move-cap exhaustion, and it refuses (not guesses) when constituent sub-game outcomes are
  invalid.
- `common/transport/series.py`'s role in settlement is disentangled from `T009`'s
  negotiation-contract scope so both can proceed without file-level collision.

## Constraints

- Do not touch reporting artifact schemas (`T016`/`T032` scope) — settlement math only.
- Do not modify the production termination guard; settlement correctly refuses the
  documented incompatible-contract cases.

## Acceptance criteria

- [ ] Group/pool series settlement is covered by a test with 3+ participants, not just pairwise.
- [ ] A series containing one unresolved (refused) sub-game outcome does not silently settle — the whole series settlement is itself flagged unresolved.
- [ ] `police_repo`'s `T039` byte-parity check passes against this task's `common/transport/series.py` diff.

## Verification

- `uv run pytest tests/unit/league`
- `uv run python scripts/check_planning_graph.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and
the exact source SHA police_repo must match.

## Result and evidence
