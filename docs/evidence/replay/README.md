# Replay CLI evidence (T047)

Sanitized `scripts/replay.py` transcripts, human and `--json`, for the three trust levels
`ADR-008` distinguishes. All identities (`game_id`, `game_uid`) and content are synthetic —
built from `tests/unit/transport/replay_fixtures.py`'s deterministic `honest_steps`/`seal`
helpers over an internal-interop bundle published by `thief_peer.reporting.replay_bundle
.publish_replay_bundle`. No secrets, private identifiers, or credentials are present.

- `honest_transcript.txt` — an untouched published bundle: `VERIFIED_OK`,
  `external_authenticity=false` (never claimed authentic even when clean).
- `tampered_transcript.txt` — one byte appended to a log file, manifest digest left stale:
  `TAMPERED`, exit code 6. The stale digest is what makes this tampering rather than an
  honest mistake.
- `unanchored_recomputed_transcript.txt` — a log record's payload, nonce, commitment, and
  the manifest's digest for that file all rewritten together, consistently, for a benign
  field. The bundle is internally consistent (`VERIFIED_OK`, `bundle_digests=true`) yet
  `external_authenticity` stays `false` and the human output states plainly that an
  unanchored bundle is never reported as authentic — this is the case ADR-008 exists to
  keep honest: an internally-consistent local rewrite must never read as "verified" in the
  sense of "historically authentic".
