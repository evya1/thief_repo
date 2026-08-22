---
id: T040
status: ready
priority: P0
task_type: governance
component: C06
optional: false
implements: []
context_files:
  - config/repo_quality.toml
  - scripts/check_line_cap.py
  - scripts/check_planning_graph.py
read_set:
  - docs/tasks/
  - docs/TODO.md
  - README.md
depends_on: []
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - config/repo_quality.toml
  - docs/tasks/T009-define-mcp-contract-and-peer-adapters.md
  - docs/tasks/T030-port-fsm-alternative-driver.md
  - docs/tasks/T016-adopt-official-report-artifact-schemas.md
  - docs/tasks/T032-internal-reporting-artifact-contract.md
  - docs/TODO.md
  - README.md
risk: low
---

# T040 — Wave W6: Quality-Gate / Module-Size and Documentation Reconciliation (thief_repo)

## Purpose

Fix the governance/tooling-visible defects found during the 2026-08-22 governance pass, and
prepare (but do not execute) the module-size remediation the line-cap gate would otherwise
require once `source_dirs` is corrected.

## Findings from this session (verified by running the checkers, not assumed)

1. `config/repo_quality.toml` has `source_dirs = []`, so the default 150-line gate never
   inspects `src/` or `common/`. Running `scripts/check_line_cap.py src common` directly
   found **6 files already over the 150-logical-line limit**:
   - `common/config/__init__.py` — 278 lines
   - `common/transport/negotiate.py` — 196 lines
   - `common/transport/series.py` — 176 lines
   - `src/thief_peer/reporting/schemas.py` — 448 lines
   - `src/thief_peer/league/preflight.py` — 165 lines
   - `common/transport/audit.py` — 154 lines
2. `scripts/check_planning_graph.py` reports 3 real issues (not resolved by this task,
   only recorded and scheduled):
   - `T030`'s `read_set` overlaps its own `write_set` on `common/transport/series.py`
     (harmless but should be trimmed).
   - `write_set` overlap between concurrent-candidate `T009` and `T030` on
     `common/transport/series.py` — this blocks `T035`/`T039` (W1/W5) from claiming until
     reconciled.
   - `write_set` overlap between concurrent-candidate `T016` and `T032` on
     `config/official/reporting/`, `src/thief_peer/reporting/schemas.py`,
     `tests/contract/report_schemas/`.

## Expected outcome (this task)

- `config/repo_quality.toml`'s line-cap section is changed to `source_dirs = ["src", "common"]`
  so the gate actually inspects production code going forward.
- `T009`/`T030` and `T016`/`T032` write-set overlaps are reconciled in the task files
  themselves (narrowed write-sets, or an explicit sequencing/`depends_on` fix) so
  `scripts/check_planning_graph.py` passes with 0 issues.
- `scripts/check_planning_graph.py` is added to the quality-gate workflow
  (`scripts/run_quality_gates.py` or CI) once the above is clean.
- README/PLAN/TODO staleness found in this session is corrected (T007's `blocked` status
  reconciled against the fact that its implementation branches — `police-strategy`/
  `thief-strategy` — already contain real strategy code; PR #36's outcome reconciled into
  `docs/TODO.md`).

## Explicitly NOT in this task's scope

- Do **not** compress code or otherwise weaken the 150-line rule to make the 6 flagged
  files pass. Splitting them behavior-preservingly is separate follow-up execution work
  under this same task's later claim, or a split-out task if the orchestrator prefers —
  either way it is implementation work, not governance, and is out of scope for the
  2026-08-22 governance/task-preparation session that authored this file.

## Acceptance criteria

- [ ] `config/repo_quality.toml` has `source_dirs = ["src", "common"]`.
- [ ] `scripts/check_planning_graph.py` reports 0 issues.
- [ ] The 6 over-limit files are each behavior-preservingly split under 150 logical lines (separate execution pass; list above is the authoritative starting inventory).
- [ ] `scripts/check_planning_graph.py` runs as part of `scripts/run_quality_gates.py` or CI.
- [ ] `docs/TODO.md` and `README.md` reflect T007's actual state and PR #36's merged outcome.

## Verification

- `uv run python scripts/check_planning_graph.py`
- `uv run python scripts/check_line_cap.py src common`
- `uv run python scripts/run_quality_gates.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers.

## Result and evidence
