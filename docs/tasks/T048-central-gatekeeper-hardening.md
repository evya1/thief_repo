---
id: T048
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
  - QR-008
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T002
  - T017
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/infra/external_api_gatekeeper.py
  - src/thief_peer/infra/gatekeeper_types.py
  - src/thief_peer/infra/retry_policy.py
  - tests/unit/infra/test_external_api_gatekeeper.py
  - tests/unit/infra/test_gatekeeper_concurrency.py
  - tests/unit/infra/test_retry_policy.py
risk: high
---

# T048 — Thread-safe deadline-aware central Gatekeeper

## Expected outcome

One `ExternalApiGatekeeper` owns global and per-service limits. Optional LLM traffic can never
consume the capacity reserved for mandatory reporting, and no retry or backoff can overrun the
turn deadline.

## Requirements implemented

- `QR-008`

## Relevant context

REVIEW_FINDINGS **F-15**: `concurrent_requests` is unused; `_active_calls` is compared against
`queue_depth` rather than a concurrency limit; state is not thread-safe; excess work is rejected
rather than queued; and retry sleeps are global `time.sleep` calls that can overrun the turn
deadline.

There is exactly one Gatekeeper. This task hardens it; it does not create a second one.

T048 depends on **T017**, which owns `infra/external_api_gatekeeper.py` and its unit test. The
dependency is what serializes that shared path; the two tasks must never run in the same wave.

## Constraints

- Edit only the declared write set.
- Preserve an adapter-compatible `execute(call, ...)` path for current reporting callers while
  introducing explicit lane and deadline arguments.
- Inject the monotonic clock and the sleeper/wait abstraction; tests use fake time, never real sleep.
- Release every counter and permit in `finally`.
- The application stays synchronous; it is not converted to asyncio to call a model provider.
- Every code and test file stays below 150 logical lines; extract typed config, errors, and retry
  classification so the coordinator stays under the cap.

## Acceptance criteria

- [x] One `Lock`/`Condition`-protected state machine enforces the global active count, the configured
      `concurrent_requests`, a bounded waiting count, the token bucket, the daily quota, and per-lane
      limits and reservations.
- [x] Excess work queues until a permit or the deadline; `QueueFull` is raised only at real capacity.
- [x] `reporting` and `llm` are distinct lanes inside the single Gatekeeper, and a saturated `llm`
      lane leaves the `reporting` reservation usable.
- [x] Retries occur only for typed or transparently classified 429/transient errors, and the
      remaining deadline budget is proven before any sleep or retry.
- [x] Tests use barriers and fake time to prove maximum concurrency, FIFO or a documented
      deterministic queue discipline, reporting reservation under LLM saturation, deadline expiry,
      daily reset, the retry schedule, and no leaked permits or counters on success or exception.
- [x] No live external call occurs in any test.

## Verification

- `uv run pytest tests/unit/infra/test_external_api_gatekeeper.py tests/unit/infra/test_gatekeeper_concurrency.py tests/unit/infra/test_retry_policy.py`
- `uv run ruff check src/thief_peer/infra tests/unit/infra`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Semantic mirror of Police T048 (`769dd6a`), reviewed and committed by the orchestrator at `851aad3`
on `claude/replay-llm-completion-20260823` (2026-08-23).

**Design.** `gatekeeper_types.py` carries `Lane = Literal["reporting", "llm"]`,
`GatekeeperConfig.reporting_reserved_slots` / `llm_max_concurrent()`, `can_admit`, and
`is_lane_head` (per-lane FIFO: a queued `llm` ticket never blocks an admissible `reporting`
ticket queued behind it). `retry_policy.py` carries pure retry classification
(`is_hard_failure`, `is_transient`, `next_backoff`, `has_budget_for`). `external_api_gatekeeper.py`
holds the single `threading.Condition`-protected `ExternalApiGatekeeper` with
`acquire_permission(lane="reporting", deadline=None)` and
`execute(call, *args, lane="reporting", deadline=None, **kwargs)`. Default lane is `"reporting"`,
so the existing `src/thief_peer/reporting/gmail.py` call site (`self.gatekeeper.execute(_raw_send)`,
no explicit lane) is unaffected — verified unchanged.

**Contended-starvation proof.** `tests/unit/infra/test_gatekeeper_concurrency.py::
test_reporting_bypasses_queued_llm_head_under_load` — one `llm` call holds the single llm slot,
a second `llm` call queues behind it, then a `reporting` call arrives and is admitted within a
1s bound via its reserved slot rather than waiting behind the queued llm ticket. Companion tests:
`test_max_concurrency_enforced`, `test_fifo_queue_discipline`,
`test_reporting_reservation_under_llm_saturation`, `test_queue_full_only_at_real_capacity`,
`test_no_leaked_permits_on_deadline_expiry`.

**Regression preserved.** All pre-existing T017 rate-bucket/DoS-lockout/daily-quota/429-retry
tests in `test_external_api_gatekeeper.py` still pass unmodified in behavior (updated only for
the new `lane`/`deadline` parameters).

**Commands run:**
```
uv run pytest tests/unit/infra/test_external_api_gatekeeper.py tests/unit/infra/test_gatekeeper_concurrency.py tests/unit/infra/test_retry_policy.py -q --no-cov
uv run ruff check src/thief_peer/infra/ tests/unit/infra/
```
Result: 24 passed, 0 failed. Ruff: all checks passed. (`--no-cov` used only because this narrow
subset alone trips the repo-wide 85% coverage gate; the full-suite run at the Replay completion
gate is the authoritative coverage check.)

**Deviations:** none from Police's design. Files split identically
(`gatekeeper_types.py` / `retry_policy.py` / `external_api_gatekeeper.py`) to respect the
150-logical-line cap.
