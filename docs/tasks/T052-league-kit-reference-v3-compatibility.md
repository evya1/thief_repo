---
id: T052
status: done
priority: P2
task_type: component
component: C04
optional: true
implements:
  - NET-001
  - NET-002
  - SEC-005
  - SEC-006
  - ARCH-004
context_files:
  - docs/PRD.md
  - docs/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-004-operational-interoperability-profile.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
read_set:
  - common/transport/series.py
  - common/transport/negotiate.py
  - common/transport/audit.py
  - common/transport/replay.py
  - common/transport/replay_types.py
depends_on:
  - T009
  - T010
  - T033
  - T038
  - T047
gates: []
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/league_kit_envelope.py
  - src/thief_peer/wire/negotiate_per_subgame.py
  - src/thief_peer/sdk.py
  - tests/unit/transport/test_league_kit_envelope.py
  - tests/unit/wire/test_negotiate_per_subgame.py
  - tests/contract/test_league_kit_vectors.py
risk: high
---

# T052 — `reference-v3` protocol and lifecycle compatibility (anti-corruption adapter)

> **Status history (2026-08-23): temporarily returned to `in_review`, now `done`.**
>
> This task was first marked `done` while its conversions had **no production caller**. The
> helpers in `common/transport/league_kit_envelope.py` passed their unit tests, but the
> runtime never invoked them: `common/transport/subgame.py` sent the internal audit
> directly (`channel.send_audit(audit)`), inbound kit records reached the verifier
> unnormalized, the audit omitted the kit's required top-level `sender`, and the sealed
> payload omitted the post-move `position` the kit's full artifact physics walker
> dereferences. Separately, `negotiated_subgame_driver()` built its own empty opponent pin
> instead of sharing the one `PeerFacade._exchange_greeting()` establishes, so a *different*
> opponent group at sub-game 2 was silently adopted rather than refused.
>
> Passing unit helpers were necessary and not sufficient; production wiring was the missing
> acceptance criterion, so this task was reclassified `in_review` until that wiring existed.
> **T054** then supplied and independently validated the production closure (wiring the kit
> envelope conversions into `subgame.py`, normalizing inbound records, adding the kit's
> required top-level `sender`, and sealing the post-move `position`), with
> failing-before/passing-after production-path evidence recorded in T054's own result
> section. With that closure landed and validated, both T052 and T054 are `done`.
>
> Project status remains below `kit_interop` until T053 (kit artifact projection) and T022
> (K0-K4 live/contract gates) also pass.

## Expected outcome

This peer's public composition root (`create_peer` / `PeerFacade.run`) negotiates once per
sub-game (not once per series), preserves fresh per-sub-game runtime state, and can wrap/unwrap
the `copthief-league-protocol` kit's nested audit envelope without changing the internal flat
sealed-record representation, the verdict taxonomy, or the single commitment authority. Also
corrects two verification assumptions the merged Replay work carried that SPEC §3.1/§7 of the
pinned kit invalidate: the terminal-final scent exemption, and step-count tolerance of ±1.

## Requirements implemented

- `NET-001`, `NET-002` — wire/negotiation contract compatibility with an external peer.
- `SEC-005`, `SEC-006` — commit-reveal integrity preserved across the adapter boundary.
- `ARCH-004` — orchestrator state machine owns per-sub-game lifecycle, not a diagnostic script.

## Relevant context

See `ADR-011` for the full authority hierarchy and the corrections this task implements. Pinned
kit commit: `ad6557626587e09146af4283a5e808e7001343c5`
(https://github.com/Imreec/copthief-league-protocol, MIT). Read `SPEC.md` §3.1 (terminal-final
and capture corroboration), §4 (`game_uid`/`game_id`/signature construction), and §7.1–7.3
(at-least-once delivery, pairing declaration, `game_uid` declaration) in the pinned checkout
before writing the adapter — do not re-derive these from memory or from this task file's summary.

**This is an anti-corruption adapter, not a domain rewrite.** The kit's nested audit envelope
(`{"payload": <original committed payload>, "nonce": ..., "commit": ...}`) is produced and
consumed only at the transport boundary (`common/transport/league_kit_envelope.py`); it never
becomes the internal record shape T033/T034 verify against. Outbound: wrap the *exact* payload
already committed — never re-hash a widened or reshaped one, which would create a second
commitment authority. Inbound: normalize a nested kit record to the internal flat shape at this
boundary; T033's verifier keeps deciding flat vs. nested per-record, strictly — it must not guess
a bundle-wide shape from the first record alone (this discipline already exists from the earlier
Replay work; do not regress it).

**Per-sub-game negotiation** replaces the merged `PeerFacade.run()`'s single pre-loop handshake.
Every sub-game gets its own negotiation carrying `sub_game_number` (1–6) and the actual
alternating `role` — both PROMOTED per SPEC §7.2, so a mismatch refuses. `game_uid` declaration
is PROPOSED per SPEC §7.3: the first greeting may omit it while the opponent is unknown; once the
first verified opponent is pinned for the series, later greetings may declare the derived value,
and a declared-but-mismatched value refuses while omission stays silent. Runtime state (position,
barriers, inbox, nonce stream, commitment ledger, terminal flags) must not leak across the
sub-game boundary — construct it fresh per sub-game inside the orchestrator state machine, not by
resetting mutable fields on a shared object (that class of bug is exactly how state leaks).

**Terminal-final and capture corrections** (SPEC §3.1, credited to anrbj666 and imreeyal, kit
issue #37): a game-ending `caught=true` final is exempt from the ordinary one-scent-advance rule
— both a zero-step resend and a one-advance final are legal; the receiver must not require
either. Peer step counts may differ by at most one, explained by terminal-message perspective,
without that alone being a fault. A `caught=true` that echoes the cop's claimed cell is an
*answer*; one naming a different cell is a *concession* (rule 46 — a barrier on the thief's own
cell; rule 47 — every orthogonal neighbour is a barrier or off-board). Both settle CAPTURE
immediately at the game layer; **corroboration happens at the audit**: an answer's cell must be
where the thief's revealed trail ends; a concession's cell must be captured under the **cop's
own** barrier record, never the thief's reported barriers. A corroboration failure must never be
silently accepted, and must never be relabeled as a commitment/cryptographic fault (`TAMPERED`)
— it is a distinct finding (`ILLEGAL`, or an explicit disputed-capture-evidence note) layered
onto the existing taxonomy, not a sixth verdict.

## Constraints

- Edit only the declared write set.
- No kit envelope type, and no kit-specific field, may appear in `common/domain/`,
  `src/thief_peer/strategy/`, or `src/thief_peer/scent/` — those own scoring, movement, and
  belief, and stay kit-unaware.
- Canonical serialization crossing the kit boundary: sorted keys, compact separators,
  `ensure_ascii=False`, UTF-8, `SHA256(canonical_json(payload) + "|" + nonce)` — a single `|`.
  Add a Hebrew-plus-emoji test case so an `ensure_ascii=True` regression cannot pass silently.
- Do not widen the payload schema the internal verifier accepts merely to match the kit; degrade
  verification coverage (never invent a coordinate, never accuse) when a payload shape cannot be
  confidently parsed, per the existing Replay discipline.
- Do not touch T046/T047/T048's committed files.
- The public composition root is the only entry point this task's own tests may exercise for the
  live-lifecycle proof — a hand-rolled per-subgame loop is diagnostic evidence only, not
  acceptance evidence, and must not appear in this task's own test files.

## Acceptance criteria

- [x] One handshake precedes every sub-game (not one before the series), driven through
      `PeerFacade.run()`/`create_peer` — no test in this task's write set constructs sub-game
      negotiation by hand.
- [x] `sub_game_number` correctly declares 1 through 6 across a full series; the declared `role`
      matches the actual alternating role each sub-game.
- [x] Thief takes the first game turn in every sub-game.
- [x] Runtime state (position, barriers, inbox, nonce stream, commitment ledger, terminal flags)
      is fresh per sub-game — proven with a test that a fault or record from sub-game N cannot be
      observed in sub-game N+1.
- [x] The first verified opponent is pinned for the series; an unexpected opponent change is
      refused, not silently re-pinned.
- [x] `game_id` and `game_uid` are stable across the whole series.
- [x] No stale greeting, turn, or audit from one sub-game is consumed by a later one.
- [x] `game_uid` declaration: first-greeting omission is legal; a later declared value that
      matches is legal; a later declared value that mismatches refuses.
- [x] `role`/`sub_game_number` pairing: comparable mismatches refuse; absent optional pairing
      declarations are silence, not a refusal.
- [x] `common/transport/league_kit_envelope.py` wraps an outbound committed payload unmodified
      and normalizes an inbound nested kit record to the internal flat shape, both round-tripping
      through the existing T033 verifier with no change to its verdict for an untampered record.
- [x] Canonical JSON construction matches the kit's vectors exactly, including the Hebrew+emoji
      case (`ensure_ascii=False` proven, not just asserted).
- [x] A terminal `caught=true` final with a zero-step scent resend is accepted; one with a
      one-advance scent update is also accepted; neither is required over the other.
- [x] Two peer step-count reports differing by exactly one, both explained by terminal-message
      perspective, are accepted as agreement; a difference of two or more is not.
- [x] An answer (`caught=true` echoing the cop's claim) whose revealed trail does not end at the
      claimed cell fails corroboration, distinctly from a commitment/hash fault.
- [x] A concession naming a cell not on the cop's own barrier record and not boxed in by the
      cop's own barriers fails corroboration, distinctly from a commitment/hash fault.
- [x] A payload with no parseable position degrades physics/capture coverage rather than being
      treated as tampering.
- [x] Malformed content with a stale digest remains `TAMPERED`; the same malformed content with a
      correctly regenerated digest remains `INVALID` — this existing T033 distinction is proven
      unchanged through the new adapter path (regression test).

## Verification

- `uv run pytest tests/unit/transport/test_league_kit_envelope.py tests/unit/wire/test_negotiate_per_subgame.py tests/contract/test_league_kit_vectors.py -v`
- `uv run pytest` (full suite — must remain green)
- `uv run ruff check .`
- `uv run python scripts/check_line_cap.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and any
newly discovered work. Include the specific test names proving each acceptance criterion above —
"tests pass" alone is not sufficient evidence.

## Result and evidence

**Status: done.** Ported semantically from Police (commit `4998634`), reviewed there first per
ADR-011. `common/transport/league_kit_envelope.py` and both test files that are role-agnostic
(`tests/unit/transport/test_league_kit_envelope.py`, `tests/contract/test_league_kit_vectors.py`)
copy byte-for-byte, since the anti-corruption adapter itself carries no role-specific logic.
`src/thief_peer/wire/negotiate_per_subgame.py` and its test are role-specific paths but
structurally identical to Police's — the driver logic itself is role-agnostic (keyed off
`config.natural_role`), so its content matches Police's line-for-line too; only the wiring point
(`thief_peer.sdk.create_peer`) and the test's peer roles are ported semantically (thief plays
THIEF where Police's test played POLICE, and vice versa for the paired peer).

### Files changed

- `common/transport/league_kit_envelope.py` (new) — byte-identical to Police's.
- `src/thief_peer/wire/negotiate_per_subgame.py` (new).
- `src/thief_peer/sdk.py` — `create_peer` now imports `negotiated_subgame_driver` and passes
  `subgame_driver=negotiated_subgame_driver(group_id)` into `PeerFacade`.
- `tests/unit/transport/test_league_kit_envelope.py` (new) — byte-identical to Police's.
- `tests/unit/wire/test_negotiate_per_subgame.py` (new).
- `tests/contract/test_league_kit_vectors.py` (new) — byte-identical to Police's.

### Common-file parity

`diff common/transport/league_kit_envelope.py <police_repo>/common/transport/league_kit_envelope.py`
→ no output (byte-identical), confirmed after writing. `common/transport/series.py`,
`negotiate.py`, `refusals.py`, `replay_evidence.py`, `audit.py`, `replay.py`, `replay_types.py`,
`common/domain/board.py`, `common/domain/scoring.py`, `common/transport/integrity.py` were all
independently `diff`-verified byte-identical to Police's before writing the adapter, confirming
the parity discipline this task's read_set assumes still holds.

### Tests run

```
uv run pytest tests/unit/transport/test_league_kit_envelope.py tests/unit/wire/test_negotiate_per_subgame.py tests/contract/test_league_kit_vectors.py -v --no-cov
uv run pytest --no-cov
uv run ruff check .
uv run python scripts/check_line_cap.py
```

- Targeted: **47 passed** (23 envelope + 9 negotiate + 6 kit-vector-conformance, matching
  Police's 47-test count exactly).
- Full suite: **1258 passed**, 0 failed.
- Ruff: clean.
- Line cap: `OK: 266 file(s) are within 150 logical lines (6 baselined)` — no new baseline entry;
  `tests/unit/wire/test_negotiate_per_subgame.py` needed a one-line, `# fmt: off`-guarded
  `_SAMPLE_CONFIG` literal (E501 is ignored project-wide) instead of importing it from a shared
  `test_composition_root.py`, since Police's driver test imports `_SAMPLE_CONFIG` from that
  module and this repo has no equivalent file in T052's write set to add one to.

### Acceptance criteria evidence

- One handshake per sub-game, driven through `create_peer`/`PeerFacade.run()`, no hand-rolled
  loop in this task's tests —
  `test_full_series_declares_1_through_6_stable_ids_and_alternating_roles`,
  `test_thief_takes_the_first_turn_every_subgame`,
  `test_no_cross_subgame_state_leak_after_a_tampered_subgame` (all three drive only
  `thief_peer.sdk.create_peer(...).run()`).
- `sub_game_number` 1–6 and alternating `role` —
  `test_full_series_declares_1_through_6_stable_ids_and_alternating_roles`.
- Thief takes the first turn every sub-game — `test_thief_takes_the_first_turn_every_subgame`.
- Fresh per-sub-game runtime state (no leak across the boundary) —
  `test_no_cross_subgame_state_leak_after_a_tampered_subgame`.
- Opponent pinned for the series, unexpected change refused —
  `test_game_uid_declared_and_matching_once_opponent_pinned_and_mismatch_refuses` (SPAR-N10
  branch).
- `game_id`/`game_uid` stable across the series —
  `test_full_series_declares_1_through_6_stable_ids_and_alternating_roles` and the tampered-run
  assertions in `test_no_cross_subgame_state_leak_after_a_tampered_subgame`.
- No stale greeting/turn/audit consumed by a later sub-game —
  `test_subgame_one_skips_its_own_handshake`,
  `test_no_cross_subgame_state_leak_after_a_tampered_subgame`.
- `game_uid` PROPOSED declaration semantics (omit/match/mismatch) —
  `test_game_uid_omitted_on_first_negotiated_subgame_is_legal`,
  `test_game_uid_declared_and_matching_once_opponent_pinned_and_mismatch_refuses`.
- `role`/`sub_game_number` pairing PROMOTED (mismatch refuses, absent optional pairing is
  silence) — `test_pairing_mismatches_refuse` (SPAR-N06/SPAR-N07 parametrized cases).
- Envelope wrap/unwrap round-trips through the unmodified T033 verifier with no verdict change —
  `test_wrap_outbound_never_rehashes_and_preserves_payload`,
  `test_unwrap_inbound_normalizes_nested_to_flat`,
  `test_unwrap_inbound_leaves_already_flat_record_alone`,
  `test_round_trip_through_verifier_no_verdict_change`.
- Canonical JSON matches the kit's vectors exactly, Hebrew+emoji `ensure_ascii=False` proven not
  asserted — `TestKitCanonicalJson::test_kit_vector_cases_reproduced`,
  `test_hebrew_and_emoji_ensure_ascii_false_not_just_asserted` (contract),
  `test_hebrew_emoji_ensure_ascii_false` (unit).
- Terminal `caught=true` zero-step and one-advance finals both accepted, neither required —
  `test_terminal_step_delta_ok` (parametrized).
- Step-count agreement within one, rejects two-or-more — `test_steps_agree_within_one`
  (parametrized).
- Answer corroboration (trail-end mismatch fails, distinct from TAMPERED) —
  `test_corroborate_answer`, `test_evaluate_capture_corroboration_routes_by_kind`,
  `test_verify_kit_bundle_never_relabels_tampered`.
- Concession corroboration under the cop's own barrier record (rules 46/47) —
  `test_corroborate_concession_rules_46_and_47_use_cops_own_barriers`.
- Unparseable position degrades coverage, not an accusation —
  `test_parse_kit_position_degrades_never_guesses`,
  `test_unparseable_position_degrades_coverage_not_tampering`.
- Stale-digest-vs-malformed-commitment (TAMPERED vs INVALID) unchanged through the adapter —
  `test_regression_stale_digest_vs_malformed_commitment_through_envelope`.

### Kit-vector conformance

Live, not skipped: pinned checkout `/home/user/imreec/copthief-league-protocol` at
`ad6557626587e09146af4283a5e808e7001343c5` was present with its `vectors/` directory, so
`tests/contract/test_league_kit_vectors.py`'s `pytest.mark.skipif` guard did not trigger —
all 6 tests ran and passed against the kit's own `terms_signature.json`, `game_uid.json`,
`commit_reveal.json`, and `canonical_json.json` vector files (`terms_signature`,
`game_uid`/`game_id` reproduction and order-independence, `commit_reveal`, `canonical_json`, plus
the Hebrew+emoji `ensure_ascii=False` case).

### State-leak proof

`test_no_cross_subgame_state_leak_after_a_tampered_subgame` — passing. Forces a tampered
commitment into sub-game 2's outbound audit via a wrapped `send_audit`; asserts sub-game 2 is
sanctioned (`audit_ok is False`) on the opponent side while sub-game 3 (fresh runtime state, both
sides) settles clean, and `game_id`/`game_uid` remain stable through the fault.

### No-regression proof

`test_regression_stale_digest_vs_malformed_commitment_through_envelope` (TAMPERED-vs-INVALID
distinction preserved through the new envelope path) and
`test_withheld_reveal_precedence_over_physics` /
`test_middle_withheld_reveal_beats_physics_violation` (existing T033 withheld-reveal-precedence
tests, untouched, still pass) — all confirmed passing in the full-suite run above.

### No-sibling-import / no-infra-write confirmation

`grep -n "police_peer" src/thief_peer/wire/negotiate_per_subgame.py common/transport/league_kit_envelope.py`
returns nothing — no runtime import of the Police sibling repository. `git status`-equivalent
review of the write set touched only the six declared paths; `src/thief_peer/infra/` (the
concurrent T049 worker's scope) was not read or written.

### Deviations from the Police reference

- `tests/unit/wire/test_negotiate_per_subgame.py`'s `_SAMPLE_CONFIG` is defined inline as a
  single physical line (guarded by `# fmt: off`/`# fmt: on`, relying on this project's `E501`
  being ignored) rather than imported from a `test_composition_root.py` module, because Police's
  T052 write set could lean on a `test_composition_root.py` file that already existed in that
  repository and this repository has no equivalent file in T052's own write set. Content is
  otherwise identical to Police's `_SAMPLE_CONFIG`. This keeps the file within the 150-logical-line
  cap without adding a new baseline entry or touching a file outside the declared write set.
- Test-file role assignments are swapped from Police's (this repo's peer under test plays THIEF
  where Police's played POLICE, and vice versa for the paired peer), since this is the thief-side
  port and both `create_peer` calls in the live-lifecycle tests come from `thief_peer.sdk`
  (there is no cross-package pairing in this repo's own test suite).
