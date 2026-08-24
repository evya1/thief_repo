---
id: T047
status: done
priority: P0
task_type: component
component: C05
optional: false
implements:
  - OBS-006
  - OBS-007
  - QR-006
context_files:
  - docs/components/C05-observability-replay/PRD.md
  - docs/components/C05-observability-replay/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T046
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/replay_service.py
  - src/thief_peer/sdk.py
  - scripts/replay.py
  - scripts/smoke_replay_integration.py
  - scripts/check_replay_parity.py
  - tests/unit/test_replay_service.py
  - tests/integration/test_replay_cli.py
  - tests/integration/test_cross_peer_replay.py
  - tests/integration/test_replay_trust_levels.py
  - tests/fixtures/replay/sibling_v1/
  - docs/evidence/replay/
risk: medium
---

# T047 — Replay application service, SDK, CLI, and cross-peer evidence

## Expected outcome

One application use case loads and verifies a published bundle. The SDK is the only programmatic
entry point; the CLI is argument parsing, printing, and exit-code mapping only. A bundle produced by
this repository verifies in the sibling repository and vice versa.

## Requirements implemented

- `OBS-006`
- `OBS-007`
- `QR-006`

## Relevant context

Implements RP-02, RP-03, RP-09, RP-11, and RP-12 of `docs/PRD_replay_port.md`. REVIEW_FINDINGS F-05: the previous
`_terms_beside()` chose the lexicographically first `config_*.json` rather than the config belonging
to the log. F-06: `cross_check_uid()` ignored malformed JSON and documents without a UID, so an empty
or incomplete directory could pass.

T015 (GUI replay view) consumes `ReplayReport` from this service and performs no hashing of its own.

## Constraints

- Edit only the declared write set.
- The CLI may import only `argparse`, `json`, `pathlib`, `sys`, and the SDK entrypoint. It contains
  no hashes, no physics, and no artifact pairing.
- No runtime import of the sibling repository; cross-peer verification copies bundle bytes only.
- Every code and test file stays below 150 logical lines.
- Evidence transcripts are sanitized; no secrets, private identifiers, or credentials.

## Acceptance criteria

- [x] The service loads exactly one UID directory, requires and validates the manifest, checks exact
      membership and per-file digests, and rejects unexpected members inside the directory.
- [x] Every log is paired with its exact config by matching `game_id`, `sub_game_index`, and
      `game_uid`. Zero matches and multiple matches are both failures, never success.
- [x] The service calls the pure `verify_replay` and aggregates a `BundleReplayReport` with stable
      JSON and human projections that print the per-layer coverage and the external-authenticity
      status explicitly.
- [x] Manifest validation also checks cross-document expected record counts and final steps (RP-12).
- [x] Exit codes: 0 verified, 4 illegal, 5 invalid or incomplete, 6 tampered, 2 path/usage error.
- [x] `src/thief_peer/sdk.py` exports `verify_replay_bundle(path) -> BundleReplayReport` as the only
      application entrypoint.
- [x] Sanitized honest, tampered, and unanchored-recomputed transcripts are generated under
      `docs/evidence/replay/`. The recomputed bundle may be internally consistent, yet it is reported
      with `external_authenticity=false` and is never described as authentic.
- [x] `scripts/smoke_replay_integration.py` and `scripts/check_replay_parity.py` implement the
      contracts in the shared test strategy: the smoke script drives the public SDK composition path
      end to end, and the parity script hashes shared bytes and invokes each repository's CLI as a
      **subprocess in that repository's own working directory**.
- [x] A bundle produced by this repository verifies with the sibling's replay CLI and vice versa,
      using frozen fixtures under `tests/fixtures/replay/sibling_v1/` or separate subprocess CLIs.
      The sibling package is never imported at runtime. `diff -rq` shows `common/` byte-identical
      across both repositories.

## Verification

- `uv run pytest tests/unit/test_replay_service.py tests/integration/test_replay_cli.py tests/integration/test_cross_peer_replay.py tests/integration/test_replay_trust_levels.py`
- `uv run python scripts/replay.py <honest-dir>`
- `uv run python scripts/smoke_replay_integration.py --help`
- `uv run python scripts/check_replay_parity.py --sibling-root ../police_repo`
- `diff -rq ../police_repo/common common`
- `uv run ruff check .`
- `uv run pytest`
- `uv run python scripts/run_quality_gates.py`

## Result and evidence

Implemented the application service, SDK entrypoint, thin CLI, and cross-peer evidence,
mirroring the sibling Police repository's already-complete T047 (commit `67fb8a3`) module for
module: `src/thief_peer/replay_service.py` (`ReplayServiceError`, `SubGameOutcome`,
`BundleReplayReport`, `verify_bundle`), `src/thief_peer/sdk.py` (new `verify_replay_bundle`
export alongside the existing `create_peer`/`validate_startup_config`), `scripts/replay.py`
(argparse + exit-code map only), `scripts/smoke_replay_integration.py` (loopback pair through
`create_peer` both sides, publish, reload via `verify_replay_bundle`), and
`scripts/check_replay_parity.py` (byte-hashes `common/` and the three shared replay test files,
then runs each repo's own CLI as a subprocess in its own cwd — never imports `police_peer`).

Frozen cross-peer fixture at `tests/fixtures/replay/sibling_v1/a1b2c3d4-e5f6-7890-abcd-ef1234567890/`
was generated with this repository's own `publish_replay_bundle`. Sanitized honest/tampered/
unanchored-recomputed transcripts are under `docs/evidence/replay/`.

### Files changed

- `src/thief_peer/replay_service.py` (new)
- `src/thief_peer/sdk.py` (added `verify_replay_bundle` + `BundleReplayReport` export; no
  existing export removed)
- `scripts/replay.py` (new)
- `scripts/smoke_replay_integration.py` (new)
- `scripts/check_replay_parity.py` (new)
- `tests/unit/test_replay_service.py` (new, 13 tests)
- `tests/integration/test_replay_cli.py` (new, 6 tests)
- `tests/integration/test_cross_peer_replay.py` (new, 5 tests)
- `tests/integration/test_replay_trust_levels.py` (new, 8 tests)
- `tests/fixtures/replay/sibling_v1/` (new frozen fixture bundle + `PROVENANCE.md`)
- `docs/evidence/replay/` (new: `honest_transcript.txt`, `tampered_transcript.txt`,
  `unanchored_recomputed_transcript.txt`, `README.md`)

### Tests run

```
uv run pytest tests/unit/test_replay_service.py tests/integration/test_replay_cli.py \
  tests/integration/test_cross_peer_replay.py tests/integration/test_replay_trust_levels.py -v
```
Result: 32 passed (`test_replay_service.py` 13, `test_replay_cli.py` 6,
`test_cross_peer_replay.py` 5, `test_replay_trust_levels.py` 8).

```
uv run pytest   (full repository suite)
```
Result: all tests pass, coverage 91.05% (>= 85% gate).

```
uv run ruff check .
```
Result: All checks passed.

```
uv run python scripts/run_quality_gates.py
```
Result: all 7 generic repository gates passed (line cap, secrets, markdown links, docs present,
task IDs, source archives, workflow permissions).

```
uv run python scripts/replay.py tests/fixtures/replay/sibling_v1/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```
Result: `VERIFIED_OK`, `external_authenticity=False`, exit code 0.

```
uv run python scripts/smoke_replay_integration.py --config config/game.json --artifact-root <tmp> --json
```
Result: real two-sided loopback series through `create_peer` (POLICE + THIEF roles), published,
reloaded, `replay_verdict: verified_ok`, exit code 0.

```
uv run python scripts/check_replay_parity.py --sibling-root ../police_repo
```
Result: `{"shared_hash_problems": []}` — `common/` and the three shared replay test files
(`replay_fixtures.py`, `test_replay_records.py`, `test_replay_verify.py`) hash byte-identical
across both repositories.

```
uv run python scripts/check_replay_parity.py --sibling-root ../police_repo --bundle-from-each --artifact-root <tmp>
```
Result: `{"shared_hash_problems": [], "reciprocal": {"ok": true, "sibling_verified_our_bundle": 0,
"we_verified_sibling_bundle": 0}}` — Police's CLI (subprocess, its own cwd) verified a bundle
this repository just published, and this repository's CLI verified a bundle Police just
published, with exit code 0 on both sides.

```
diff -rq ../police_repo/common common
```
Result: only `__pycache__/*.pyc` differ (bytecode caches embed absolute paths); every `.py`
source file is byte-identical, consistent with the parity script's own `*.py`-only hash scope.

### Verdict/exit-code and trust-level proofs

- Exit-code table (0/4/5/6/2) confirmed against Police's `_EXIT_BY_VERDICT` map, byte-identical
  logic in `scripts/replay.py`; exercised by `test_replay_cli.py`'s six tests including the
  path/usage-error case (`test_missing_path_exits_two`).
- TAMPERED vs INVALID (stale digest vs recomputed-and-matching): proven by
  `test_replay_trust_levels.py::test_one_byte_semantic_mutation_is_tampered` (stale commit,
  `commitment_mismatch` -> tampered) and
  `test_replay_trust_levels.py::test_recomputed_unanchored_bundle_verifies_but_is_never_authentic`
  (payload+commit+manifest digest rewritten consistently -> verified_ok,
  `external_authenticity=false`), plus `test_replay_service.py::test_digest_mismatch_against_manifest_is_tampered`
  for the manifest-level stale-digest case.
- Withheld-committed-reveal precedence over a plain sequence gap, proven at the **bundle
  aggregation layer** (not just the shared `verify_replay`): new tests
  `test_replay_trust_levels.py::test_bundle_level_withheld_reveal_outranks_plain_gap` (drops a
  record, adds `own_committed_steps` covering it -> sub-game and bundle verdict `TAMPERED` with
  a `withheld_reveal` issue) and
  `test_replay_trust_levels.py::test_bundle_level_plain_gap_without_ledger_is_invalid` (same gap,
  no commitment ledger -> sub-game verdict `INVALID` with a `skipped_step` issue, no
  `withheld_reveal`).

### No-sibling-import confirmation

`grep -rn "police_peer" src/ scripts/ tests/` returns only: the `police_peer` name inside a
docstring comment and inside `test_sibling_repository_never_imported`'s runtime assertion in
`tests/integration/test_cross_peer_replay.py` — no `import police_peer` anywhere, and
`grep -rn "sys.path" src/ scripts/` returns only a docstring line in `check_replay_parity.py`
describing that it *never* does so.

### Deviations from the Police reference

- `scripts/smoke_replay_integration.py`'s `_run_pair` returns `results["thief"]` (the
  thief-side `SeriesResult`) rather than Police's `results["police"]`, since this is the
  thief-side smoke test and the bundle content is symmetric either way — a naming-only change,
  no behavioral difference from Police's script.
- The withheld-reveal-vs-plain-gap bundle-aggregation regression tests (required by this task's
  own instructions beyond what Police's committed T047 tests cover) were added to
  `tests/integration/test_replay_trust_levels.py` rather than `tests/unit/test_replay_service.py`
  to keep both files under the 150-logical-line cap (`test_replay_service.py` would have been
  160 lines with them inline).
- `docs/evidence/replay/` includes a short `README.md` describing provenance and sanitization,
  in addition to the three required transcripts.
