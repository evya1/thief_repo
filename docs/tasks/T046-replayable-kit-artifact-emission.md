---
id: T046
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
  - OBS-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T034
gates:
  - id: INPUT-001
    kind: input
    scope: official_templates
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/thief_peer/reporting/replay_documents.py
  - src/thief_peer/reporting/replay_bundle.py
  - src/thief_peer/runner.py
  - tests/unit/reporting/test_replay_documents.py
  - tests/unit/reporting/test_replay_bundle.py
  - tests/integration/test_replay_bundle_publish.py
  - tests/integration/test_replay_bundle_concurrency.py
risk: medium
---

# T046 — Internal-interop documents and atomic replay bundle

## Expected outcome

After a settled series the runner publishes exactly one complete replay bundle at
`<artifact_root>/replay/<game_uid>/`, or publishes nothing at all. Every emitted document is
explicitly labelled `internal_interop`; nothing is described as official.

## Requirements implemented

- `REPORT-005`
- `REPORT-006`
- `REPORT-007`
- `REPORT-008`
- `REPORT-009`
- `OBS-006`

## Relevant context

Implements RP-03, RP-07, RP-08, and RP-12 of `docs/PRD_replay_port.md`. REVIEW_FINDINGS F-10: artifact
writes are independent `write_text` calls, so a crash or cancellation can leave a partially
valid-looking bundle. F-11: the official templates are absent, so a guessed official schema would
create false compliance.

## Gates

- `INPUT-001` (`input`, `blocks: criterion`) — only the official-schema acceptance criterion waits.
  Internal-interop implementation is not blocked. `{#official_templates}`

## Constraints

- Edit only the declared write set. Do **not** extend `reporting/pipeline.py` and do not replace the
  existing result summary output.
- Build every byte in memory first, then stage, then publish.
- Never overwrite an existing UID directory; an existing destination fails closed.
- Every code and test file stays below 150 logical lines.
- No guessed official schema, no DI framework, Repository/Unit of Work, or event bus.

## Acceptance criteria

- [x] Pure builders emit deterministic declaration, config, log, result, and manifest dictionaries.
      All carry `schema_version`, `artifact_kind`, `schema_status: internal_interop`, non-empty
      `game_uid` and `game_id`, config/log pairs carry the same `sub_game_index`, and cross-document
      expected record counts and final steps agree for both halves (RP-12), so a truncated final
      record cannot pass merely because the remaining sequence is contiguous.
- [x] Serialization is UTF-8 with stable key ordering and a trailing newline.
- [x] The writer creates `<root>/replay/.<uid>.staging-<random>` with mode 0700, writes the exact
      member set, flushes and **fsyncs** files and the staging directory where supported, computes
      digests, reloads and self-verifies all six config/log pairs, acquires an **O_EXCL publication
      lock**, renames once, and fsyncs the parent directory where supported.
- [x] The manifest lists exact member names and SHA-256 file digests: one declaration, six configs,
      six non-empty logs, one result.
- [x] Failure injected after each individual write, after fsync, and at publish leaves no destination
      directory and no staging residue; cleanup happens in `finally`.
- [x] An existing destination is never overwritten, and a stale publication lock is reported for
      T022 recovery rather than silently deleted.
- [x] Two concurrent publishers race for the same UID: exactly one wins, the loser fails closed, and
      the winner's bundle is never overwritten or partially observed.
- [x] Integration test publishes a bundle from a real settled series and verifies exact counts,
      digests, and identity.
- [x] No document claims official-schema compliance while `INPUT-001` is unresolved.
      `{#official_templates}`

## Verification

- `uv run pytest tests/unit/reporting/test_replay_documents.py tests/unit/reporting/test_replay_bundle.py tests/integration/test_replay_bundle_publish.py tests/integration/test_replay_bundle_concurrency.py`
- `uv run ruff check src/thief_peer/reporting src/thief_peer/runner.py tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Semantic mirror of the equivalent implementation already accepted in `police_repo`
(commit `19c9c0f`, ADR-009), ported onto Thief's own naming/module layout. `common/`
replay core (`replay.py`, `replay_evidence.py`, `replay_layers.py`, `replay_records.py`,
`replay_types.py`, `series.py`, `domain/scoring.py`) is byte-identical between the two
repositories (`diff` confirmed), so `SeriesResult`/`SeriesRow`/`SubgameReplayEvidence`
required no adaptation; only the `police_peer` → `thief_peer` import path changed.

Files added (write set as declared):
- `src/thief_peer/reporting/replay_documents.py` — pure builders for declaration/config/
  log/result/manifest, all carrying `schema_status: internal_interop`; `check_completeness`
  re-checks a reloaded log against the manifest's RP-12 counts.
- `src/thief_peer/reporting/replay_bundle.py` — `publish_replay_bundle`: build-in-memory,
  stage into `<root>/replay/.<uid>.staging-<random>` (mode 0700), write+flush+fsync every
  member, fsync the staging dir, self-verify by reloading and re-running `verify_replay`,
  acquire an O_EXCL publication lock, re-check destination existence, rename once, fsync
  the parent dir, release the lock. All failure paths run through a single `finally` that
  removes staging residue and never touches an already-acquired lock file.
- `tests/unit/reporting/test_replay_documents.py`, `tests/unit/reporting/test_replay_bundle.py`
  — unit coverage for document shape/labelling/digests/completeness and for staging,
  self-verify, locking, rename, and failure-injection cleanup.
- `tests/integration/test_replay_bundle_publish.py` — publishes from a real settled
  loopback series (`StandInEngine` both sides) and verifies exact member count, manifest
  digests, and per-sub-game `verify_replay` non-INVALID/INCOMPLETE verdicts; also proves
  the existing `result_<game_id>.json` summary artifact is untouched by bundle publication.
- `tests/integration/test_replay_bundle_concurrency.py` — two threads race the same UID
  with a barrier synchronized at `after_self_verify` so the O_EXCL lock decides the
  outcome; exactly one wins, the loser gets a typed `PublicationLockError` or
  `ReplayBundleExistsError`, and the winner's 15-member bundle is left intact.

Deviation from the parent orchestrator's message write set (documented, not silent): the
message text omitted `tests/unit/reporting/test_replay_documents.py`, but T046's own
`write_set` frontmatter (this file) names it, and folding all builder + publication tests
into one `test_replay_bundle.py` file exceeded the 150-logical-line cap (165 lines) exactly
as it did for Police, who split for the same reason. Split along the same seam Police used.
`src/thief_peer/runner.py` was left untouched — it already exposes `write_artifacts` with
the exact shape T046 depends on (verified via `test_existing_summary_artifact_output_is_unchanged`)
and needed no edit.

Verification run from repository root:

```
uv run pytest tests/integration/test_replay_bundle_concurrency.py tests/integration/test_replay_bundle_publish.py tests/unit/reporting/test_replay_bundle.py -v
# 13 passed (coverage gate fails on this narrow subset only because --cov-fail-under=85
# is repo-wide in pyproject.toml addopts and this slice alone can't reach 85% of the
# whole codebase; the full-suite run below reaches 93.62% and exits 0)
uv run pytest -q
# 93.62% coverage, exit 0
uv run ruff check src/thief_peer/reporting/ tests/integration/ tests/unit/reporting/
# All checks passed!
uv run python scripts/check_line_cap.py
# OK: 158 file(s) are within 150 logical lines
```

No claim of official-schema compliance or external authenticity exists anywhere in the
new code, docstrings, or this file; `schema_status: internal_interop` is applied
unconditionally to every emitted document via `_base()`.
