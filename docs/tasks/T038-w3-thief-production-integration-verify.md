---
id: T038
status: done
priority: P1
task_type: component
component: C02
optional: false
implements:
  - S3a
  - S3b
  - S3c
  - FR-T2
  - FR-T3
  - H2
  - H3
  - H4
  - H5
context_files:
  - docs/mechanisms/M-04-thief-strategy.md
read_set:
  - src/thief_peer/wire/session.py
  - src/thief_peer/sdk.py
depends_on:
  - T037
gates: []
parallel_safe: true
claimed_by: ORC
claim_expires_at:
write_set:
  - docs/tasks/T038-w3-thief-production-integration-verify.md
risk: low
---

# T038 — Wave W3b: Thief Production-Integration — Verification Record (thief_repo)

## Purpose

This task exists to give the production-integration half of W3 an explicit governance
record, since the substance is **already satisfied** by `evya1/thief_repo#36` (merged,
green/mergeable at review time; base `thief-strategy` `f506bd8`, head `5c300bb`). No
further `src/` change is scoped here. If a genuine gap is later found, it gets its own
new task per AGENTS.md — this task's write set stays docs-only.

## Evidence that production-integration is already satisfied

- `sdk.py`'s `create_peer` returns `BrainDrivenEngine` for the THIEF role by default (real
  brain wired in production, not the `StandInEngine`).
- `BrainDrivenEngine` runs every received half-turn through the canonical
  `apply_half_turn` order and normalizes incoming scent via `wire/evidence.py` before it
  reaches belief/brain (H3).
- `SubgameSession` is extracted as a shared mutable lifecycle owner composed by both
  `StandInEngine` and `BrainDrivenEngine` (no fragile subclassing).
- The KPI harness (TC-T17) evaluates every THIEF sub-game across a series (never `any()`)
  against an opponent that actually pursues and claims capture (`GreedyCapturingPolice`),
  with a mandatory always-STAY negative control recording an actual CAPTURE.
- `uv run ruff check .`, `uv run pytest`, `uv run python scripts/run_quality_gates.py` all
  reported passing in PR #36's own verification section.

## Acceptance criteria

- [x] Real `ThiefBrain` is wired in production `sdk.py`, not a stand-in, for the THIEF role.
- [x] KPI harness exercises a capturing opponent and every sub-game, with a negative control.
- [x] Evidence normalization exists at the wire boundary before belief/brain.

## Result and evidence

Closed by reference to `evya1/thief_repo#36` (merged 2026-08-22T07:03:12Z). No `src/`
changes made by this governance task. Recorded 2026-08-22 during the W1-W6
governance/task-preparation pass.
