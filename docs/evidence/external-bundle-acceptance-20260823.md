# External Bundle Acceptance — Thief — 2026-08-23

`M006 — External Bundle Handoff Acceptance`. Maintenance/evidence task.
Requirement IDs: ARCH-008, QR-001, QR-002, QR-004, QR-006, QR-010, QR-011, QR-019, SUB-001.

The pinned kit commit `ad6557626587e09146af4283a5e808e7001343c5` is represented by the
vendored fixtures under `tests/fixtures/league_kit/ad65576/`. All four vector hashes were
reproduced exactly (see `Reproduced commands`). This is `kit_interop` evidence only.

## Git state

| Field | Value |
|---|---|
| Repository | `github.com:evya1/thief_repo` |
| Local branch | `lahav-tasks` |
| HEAD | `6679df494261b6803ca0e92a4f2113f3bdc5544a` |
| Remote feature head (`origin/claude/replay-llm-completion-20260823`) | `6679df494261b6803ca0e92a4f2113f3bdc5544a` |
| `origin/master` | `14c05939e833f57a95fc97a298645f5e1e0b1fa6` |
| Dirty worktree | clean (no tracked changes) |
| Unpushed commits | 0 (HEAD equals remote feature head) |
| Divergence from remote feature head | 0 left / 0 right |

The local `lahav-tasks` branch is byte-identical to the pushed external feature branch head.
No upstream is configured; the remote feature head is used as the acceptance anchor.

## Commit-to-task map

Commits on `origin/master..HEAD` (newest first):

| SHA | Task/scope |
|---|---|
| `6679df4` | docs: hunk-level provenance map for the llm-provider partner branch (Thief port) |
| `2524949` | T054 wire reference-v3 audit adapter, stable opponent pin, sealed position (Thief port) |
| `5e1f91a` | docs: reconcile actual kit checkpoint status and resolve PLANQ-007 (Thief port) |
| `b47aca6` | T052 reference-v3 protocol and lifecycle compatibility (Thief port) |
| `d066cbe` | T049 provider-neutral language model adapter (Thief port) |
| `ba065b5` | docs: narrow README correction from verified branch state (T023/T024/T026 remain open) |
| `a237bed` | Governance: ADR-011, T052, T053, amended T022 for league-kit interoperability (Thief port) |
| `f719d19` | T040 (partial): honest production line-cap ratchet, source_dirs blind spot repaired (Thief port) |
| `1a6c957` | T047 orchestrator validation — status in_review to done |
| `db22fb4` | T047 headless Replay application service, SDK entrypoint, thin CLI (Thief port) |
| `8229e74` | T048 record orchestrator-reviewed status and evidence in the task packet |
| `851aad3` | T048 thread-safe, deadline-aware central Gatekeeper with per-lane admission (Thief port) |
| `6d088ac` | T046 atomic internal-interop Replay bundle publication (Thief port) |

## Changed-file/write-set audit

The changed files map to the declared external write sets (T046, T047, T048, T049, T052,
T054, T040, governance/ADR-011, T022 amendment, provenance docs, README/TODO corrections).
No unexpected production files were observed. Representative changed paths:

- `common/transport/*` (audit_physics, audit_wire, league_kit_envelope, opponent_pin,
  replay_evidence, run_series, series, subgame)
- `src/thief_peer/infra/*` (external_api_gatekeeper, gatekeeper_types, llm_client,
  llm_provider, retry_policy)
- `src/thief_peer/replay_service.py`, `src/thief_peer/reporting/replay_*`
- `src/thief_peer/sdk.py`, `src/thief_peer/wire/*`
- `docs/decisions/ADR-011-league-kit-interoperability-boundary.md`
- `docs/provenance/llm-provider-branch-reconciliation.md`
- `docs/evidence/replay/*` (honest/tampered/unanchored transcripts)
- `docs/tasks/T022/T040/T046/T047/T048/T049/T051/T052/T053/T054*.md`
- `tests/fixtures/league_kit/ad65576/*`, `tests/fixtures/replay/sibling_v1/*`
- `scripts/check_replay_parity.py`, `scripts/replay.py`, `scripts/smoke_replay_integration.py`
- `config/repo_quality.toml`

## Reproduced commands

| Command | Exit | Summary |
|---|---|---|
| `git rev-parse HEAD` | 0 | `6679df494261b6803ca0e92a4f2113f3bdc5544a` |
| `git status --short --branch` | 0 | `## lahav-tasks` (clean) |
| `git diff --check` | 0 | no whitespace errors |
| `git rev-list --left-right --count origin/claude/replay-llm-completion-20260823...HEAD` | 0 | `0 0` (identical) |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run pytest -q` | 0 | 5270 statements, 457 missing, coverage 91.33% (>=85%) |
| `uv run python scripts/run_quality_gates.py` | 0 | all 7 generic gates passed |
| `uv run python scripts/check_line_cap.py` | 0 | 275 files within 150 lines (5 baselined) |
| `uv run python scripts/check_replay_parity.py --sibling-root ../police_repo` | 0 | shared_hash_problems: [] |
| `sha256sum vectors/*.json` (kit fixtures) | 0 | all four match pinned PROVENANCE.md hashes |

## External scope verdicts

| Scope | Verdict | Basis |
|---|---|---|
| Governance / M000 / PR truth | `accepted` | ADR-011, provenance map, README/TODO corrections present and coherent |
| T052/T054 kit runtime closure | `accepted` | T052/T054 commits present; kit fixtures pinned and verified |
| Partner provenance / component docs | `accepted` | provenance map present |
| Replay / provider / kit evidence | `accepted` (fixture-level) | replay parity clean; kit vector hashes verified |

## Interop labels

| Label | Verdict |
|---|---|
| `internal_interop` | `accepted` — Replay parity clean, cross-peer replay tests present |

## Accepted head

`EXTERNAL_ACCEPTED_HEAD` (Thief) = `6679df494261b6803ca0e92a4f2113f3bdc5544a`

## Branch continuation

The external feature branch `claude/replay-llm-completion-20260823` is open, clean, and its
remote head equals the accepted head. Per the v6 continuation rule, v6 continues this same
feature branch (locally named `lahav-tasks`). No new branch is created. Never commit to
`master`, force-push, rewrite, or auto-merge.
