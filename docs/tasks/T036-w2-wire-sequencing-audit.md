---
id: T036
status: blocked
priority: P0
task_type: component
component: C03
optional: false
implements:
  - ARCH-002
  - ARCH-003
  - NET-001
context_files:
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - common/transport/negotiate.py
  - common/transport/audit.py
read_set:
  - src/thief_peer/wire/session.py
depends_on:
  - T035
  - T009
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/negotiate.py
  - common/transport/audit.py
  - src/thief_peer/wire/session.py
  - tests/unit/transport/
  - tests/unit/wire/
risk: medium
---

# T036 — Wave W2: Validated Wire, Role-Correct Sequencing, Capture Ack, Audit Idempotency (thief_repo)

`thief_repo` is source-of-truth for the shared `common/transport/{negotiate,audit}.py` edits
in this wave; `police_repo` runs the required byte-parity check in its own `T036`.

## Expected outcome

- Every inbound wire message is validated against the negotiated contract before it reaches
  belief/strategy (extends the H3 evidence-normalization pattern already landed for scent in
  PR #36 to the general wire-validation boundary).
- Role-correct half-turn sequencing is enforced (Thief-first, per `ADR-001`) with a typed
  rejection for an out-of-order or replayed message.
- Capture acknowledgement is a first-class, required step: a capture claim is not treated as
  resolved until the claimed-against role's acknowledgement (or a timed-out refusal) is
  recorded in the audit trail.
- Re-processing an already-audited event (retry/duplicate delivery) is idempotent: the audit
  log does not double-record and scoring does not double-count.

## Constraints

- Do not widen into `T035`'s termination scope or `T019`'s scoring scope.
- No guessed schema; reject malformed input rather than coercing it (mirrors H3's "never raise
  on hostile input, but never guess" discipline from PR #36's `wire/evidence.py`).

## Acceptance criteria

- [ ] A message arriving out of role-turn-order is rejected with a typed error and does not mutate game state.
- [ ] A capture claim has an explicit acknowledgement/refusal step recorded in the audit trail before it affects scoring.
- [ ] Replaying an already-processed audited message is a no-op (idempotent), verified by a test that delivers the same message twice.
- [ ] `police_repo`'s `T036` byte-parity check passes against this task's shared-file diff.

## Verification

- `uv run pytest tests/unit/transport tests/unit/wire`
- `uv run python scripts/check_planning_graph.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and the
exact source SHA police_repo must match.

## Result and evidence
