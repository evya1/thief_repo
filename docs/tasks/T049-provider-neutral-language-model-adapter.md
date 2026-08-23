---
id: T049
status: done
priority: P2
task_type: component
component: C06
optional: true
implements:
  - STRAT-008
  - QR-008
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T027
  - T048
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/infra/llm_client.py
  - src/thief_peer/infra/llm_provider.py
  - tests/unit/infra/test_llm_provider.py
  - tests/contract/test_llm_provider_contract.py
risk: medium
---

# T049 — Provider-neutral language model adapter

## Expected outcome

A vendor-neutral adapter turns a `HintRenderRequest` into a deterministic prompt, calls an injected
one-method client exclusively through the Gatekeeper's `llm` lane, and normalizes the response into
a frozen `ProviderReply`. No vendor SDK, no environment read, and no network fixture appear here.

## Requirements implemented

- `STRAT-008`
- `QR-008`

## Relevant context

Implements LLM-06 and LLM-07 of `docs/PRD_llm_provider.md`. REVIEW_FINDINGS **F-16**: provider usage
has no typed boundary and the existing hint result is a mutable `dict[str, str]`, so token totals
cannot be traced reliably into sealed evidence.

The selected vendor's transport is T050 and is separately gated by `PLANQ-003`.

## Constraints

- Edit only the declared write set.
- Define the one-method `CompletionClient` `Protocol` next to its consumer; no vendor import, no
  dependency addition, no environment lookup, no vendor name in this task.
- Reuse the strategy-owned request/reply types from T027 rather than redefining them.
- Every code and test file stays below 150 logical lines.
- No live external call in any test.

## Acceptance criteria

- [x] The prompt is versioned and deterministic, built only from allowlisted `HintRenderRequest`
      fields, and requests plain text rather than model-owned JSON semantics.
- [x] The injected client is called only via `ExternalApiGatekeeper.execute(lane="llm", ...)` with the
      passed deadline.
- [x] One client response normalizes into `ProviderReply` with provider and model identifiers and
      optional nonnegative token counts.
- [x] Booleans and negative usage values, and oversized or empty raw text, are rejected with typed
      adapter errors that `HintWriter` maps to a deterministic fallback.
- [x] Unknown usage stays `None`; token counts are never inferred from the text.
- [x] Contract tests run fake clients for success, timeout, 429 retry, missing usage, malformed types,
      and the privacy allowlist, and assert zero live network access.

## Verification

- `uv run pytest tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py`
- `uv run ruff check src/thief_peer/infra tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Ported semantically from `police_repo` commit `887b476`
(`src/police_peer/infra/llm_client.py`, `src/police_peer/infra/llm_provider.py`, and their
unit/contract test files), renaming `police_peer` -> `thief_peer` and `Role.POLICE` ->
`Role.THIEF` only; no other logic changed. Reuses T027's `HintRenderRequest`/`TokenUsage`/
`ProviderReply`/`TextProvider` from `thief_peer/strategy/hint_types.py` unchanged, and T048's
`ExternalApiGatekeeper.execute(lane="llm", deadline=...)` unchanged.

**Files added:**
- `src/thief_peer/infra/llm_client.py` (41 lines) -- `CompletionClient` Protocol, `RawCompletion`.
- `src/thief_peer/infra/llm_provider.py` (137 lines) -- `build_prompt`, `LanguageModelAdapter`,
  `LlmAdapterError` and its `MalformedResponseError`/`MalformedUsageError`/`InvalidOutputTextError`
  subclasses.
- `tests/unit/infra/test_llm_provider.py` (116 lines) -- 14 tests: prompt versioning/determinism/
  allowlist/plain-text, usage normalization, text normalization.
- `tests/contract/test_llm_provider_contract.py` (172 lines) -- 12 tests: Gatekeeper `llm`-lane
  wiring, deadline preservation, retry/timeout, usage/text rejection, privacy allowlist, zero-network.

**Tests run:**
```
uv run pytest tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py -v --no-cov
uv run pytest --no-cov
uv run ruff check src/thief_peer/infra tests
uv run python scripts/check_line_cap.py
```

**Results:**
- Targeted suite: 26 passed (14 unit + 12 contract).
- Full suite: 1211 passed.
- Ruff (`src/thief_peer/infra tests`): all checks passed.
- Line cap: all four new files are within the 150-logical-line cap (41/137/116/172 raw lines,
  well under cap after excluding blank/comment lines). The one `check_line_cap.py` FAIL reported
  (`tests/unit/wire/test_negotiate_per_subgame.py`, 178 lines) is a pre-existing file outside this
  task's write set, produced by the concurrent T052 sibling worker; not touched or introduced by
  this task.

**Acceptance-criteria evidence:**
1. Versioned/deterministic/allowlist/plain-text prompt: `test_prompt_is_versioned`,
   `test_prompt_is_deterministic_for_identical_request`, `test_prompt_changes_with_claim`,
   `test_prompt_requests_plain_text_not_json`, `test_prompt_contains_only_allowlisted_fields`.
2. Client reached only via `Gatekeeper.execute(lane="llm", ...)` with passed deadline:
   `test_client_reached_only_through_llm_lane_execute`, `test_deadline_is_preserved_not_reset`.
3. Response normalizes into `ProviderReply`: `test_success_normalizes_to_provider_reply`,
   `test_normalize_usage_known_counts`.
4. Typed rejection of bool/negative usage and oversized/empty text:
   `test_normalize_usage_rejects_bool`, `test_normalize_usage_rejects_negative`,
   `test_malformed_usage_bool_is_rejected`, `test_malformed_usage_negative_is_rejected`,
   `test_empty_output_text_is_rejected`, `test_oversized_output_text_is_rejected`,
   `test_normalize_text_rejects_empty`, `test_normalize_text_rejects_oversized`.
5. Unknown usage stays `None`: `test_normalize_usage_none_stays_none`,
   `test_missing_usage_stays_none_not_inferred`.
6. Contract fakes cover success/timeout/429-retry/missing-usage/malformed/privacy/zero-network:
   `test_success_normalizes_to_provider_reply`, `test_timeout_raises_and_never_returns_a_reply`,
   `test_retryable_429_then_success`, `test_missing_usage_stays_none_not_inferred`,
   `test_malformed_usage_bool_is_rejected`, `test_privacy_allowlist_disallowed_field_never_reaches_prompt`,
   `test_zero_live_network_uses_fakes_only`.

**Privacy allowlist proof:** `test_privacy_allowlist_disallowed_field_never_reaches_prompt`.

**Gatekeeper lane proof:** `test_client_reached_only_through_llm_lane_execute`.

**Deviations:** none -- semantic port only (module path and `Role` member renamed to Thief's own).

**Blockers:** none.
