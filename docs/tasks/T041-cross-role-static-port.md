---
id: T041
status: blocked
priority: P2
task_type: component
component: C02
optional: true
implements: []
context_files:
  - docs/decisions/ADR-007-cross-role-strategy-port.md
read_set: []
depends_on:
  - T038
gates:
  - id: SIBLING-W4-LANDED
    kind: cross-repo
    scope: police_repo T037/T038
    blocks: start
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/opponents/reference_police.py
  - tests/integration/test_strategy_selfplay_kpi.py
risk: low
---

# T041 — Cross-Role Static Port: Reference Police Opponent (thief_repo)

Per `ADR-007`. Ports a point-in-time, statically-reviewed copy of `police_repo`'s accepted
Police strategy (`T037`/`T038` outcome) into `thief_repo`, for KPI/self-play evaluation
only — never for thief_repo's own production move selection, never as a runtime import.

## Constraints

- Cannot start until `police_repo`'s `T037` (strategy core) and `T038` (production
  integration) are both accepted — porting an unstable policy defeats the purpose.
- The ported file carries a header comment recording: source repo, source commit SHA, port
  date, and "evaluation-only — do not wire into `sdk.py`".
- No runtime cross-repo import, no shared live module, no network call between the two
  repositories for this purpose.

## Acceptance criteria

- [ ] `src/thief_peer/opponents/reference_police.py` exists with correct provenance header.
- [ ] It is exercised only from `tests/integration/test_strategy_selfplay_kpi.py` (or equivalent KPI/self-play paths), never from `sdk.py`.
- [ ] A later re-port is a separate, reviewed change to this same file (not silent drift).

## Verification

- `uv run pytest tests/integration/test_strategy_selfplay_kpi.py`
- Manual review confirms no import of this module from `src/thief_peer/sdk.py` or `wire/`.

## Handoff contract

Report files changed, tests executed, exact results, source SHA ported, decisions, blockers.

## Result and evidence
