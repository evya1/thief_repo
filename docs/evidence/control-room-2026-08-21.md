# Police/Thief — Control-Room Session Checkpoint
Date: 2026-08-21 · Branch: `claude/police-thief-reconnaissance-v17a8i` (both repos)

## A. Executive outcome

The session opened on two repos with ~5,500 lines of well-tested library code and
**no production execution path**: no installable package, no entrypoint, no strategy,
and the flagship perception subsystems (scent, belief) unreachable from the code that
plays a turn. The session merged the runtime boundary (police #32, thief #33), which
made the peers executable, then ran the **first genuinely complete Police↔Thief game**:
two separate OS processes, real FastMCP HTTP, six sub-games, role alternation,
`audit_ok` on every row, matching `game_uid`, clean shutdown. Six cross-component
defects were reproduced and fixed with regression tests. Both masters are usable for
the next implementation wave. What remains open: thief #34 (strategy) needs rework,
and the game is still strategically degenerate — no peer has a policy, so every
sub-game ends in thief survival at 35 steps.

## B. Session activity ledger

1. Fetched both repos, recorded master SHAs, enumerated all branches and PRs.
2. `uv sync --locked --all-groups` both repos; baseline **734 passed** each, ruff clean, 7/7 gates.
3. Six bounded read-only subagents run to completion (police state, thief state,
   branch/PR integrator, OPEN/PLANQ auditor, cross-repo bug hunter, strategy reviewer).
4. Discovered PR #32/#33 add `strategy.py` while the strategy branches add `strategy/`
   — proved the merged tree is unimportable (47 collection errors), order-independent.
5. Verified pair A (master + #32/#33): 755 passed both repos, gates green.
6. Ran real cross-repo two-process E2E → merged police #32 (`69e234e`), thief #33 (`f4af4d9`).
7. Fixed 6 defects across 3 commits per repo, each with a failing-first regression test.
8. Posted NEEDS_REWORK review on thief #34 with two reproduced blockers.
9. Opened police #33 and thief #35 for the fixes.

Mistakes made and corrected, for the record:
- Two `cd`-context slips early on made one repo's output masquerade as the other's;
  caught within a turn and re-run with explicit `git -C` everywhere afterwards.
- A blanket `sed 's/police_peer/thief_peer/g'` corrupted thief role defaults
  (`Role.POLICE`, `"police-local"`); reverted via `git checkout --` and replaced with a
  targeted patch. Verified clean afterwards.
- An `EXIT=$?` after a pipe captured `tail`'s status, masking a real gate failure;
  re-measured correctly.
- A regression test pushed a file past the 150-logical-line gate; split into a
  dedicated test file.

## C. Git and GitHub change table

| | Police | Thief |
|---|---|---|
| Starting master | `df003a3` | `e250f91` |
| After runtime-boundary merge | `69e234e` (PR #32) | `f4af4d9` (PR #33) |
| **Final master** | **`837137f`** (PR #33) | **`4b32693`** (PR #35) |
| Fix branch HEAD | `d595ab6` (merged) | `0b7df71` (merged) |
| Commits on branch | `3f30e72`, `5d70822`, `d595ab6` | `f418218`, `06a6902`, `0b7df71` |
| Fix PR | **#33 MERGED** 21:55:20Z | **#35 MERGED** 21:54:44Z |
| Local == remote | yes | yes |
| Working tree | clean | clean |

Merged this session: police #32 + thief #33 (runtime boundary, merged by this session);
police #33 + thief #35 (six-defect remediation, **merged externally**, not by this session).
Reviewed: thief #34 (NEEDS_REWORK) + factual status note after #35 landed.
Newly observed: **police #34 "Police strategy"** (head `police-strategy`, `5f7c3bf`) is now OPEN.

Post-merge smoke on the merged masters: real two-process cross-repo six-sub-game FastMCP
HTTP series, `audit_ok` on all 6 rows, matching `game_uid`, both processes exit 0.

## D. Defect disposition

| # | Defect | Sev | Disposition | Commit | Test |
|---|---|---|---|---|---|
| 1 | Audit passes on empty/partial reveal | BLOCKER | FIXED | `3f30e72`/`f418218` | `test_withheld_reveal_is_tampered`, `test_partial_reveal_hiding_the_tampered_step_is_tampered` |
| 2 | Cop sanctioned for a legal missed capture claim | BLOCKER | FIXED | same | `test_capture_claim_that_misses_is_legal_play` |
| 3 | Belief diffusion resurrects excluded barriers | MEDIUM | FIXED | same | `test_diffuse_never_resurrects_an_excluded_cell`, `test_diffuse_keeps_every_earlier_barrier_excluded` |
| 4 | 85% coverage gate inert (no `--cov`) | MEDIUM | FIXED | same | enforced in-band; 92.40%/92.07% |
| 5 | BH-04 scent lock never declared | BLOCKER | FIXED | `5d70822`/`06a6902` | `tests/contract/test_scent_config_lock.py` (3) |
| 6 | BH-10 budgets dict vs Protocol | HIGH | FIXED | `d595ab6`/`0b7df71` | `tests/unit/wire/test_config_budgets.py` (4) |
| — | thief #34 B1: strategy never receives scent/belief (0/60 vs 60/60) | BLOCKER | REPORTED, not fixed | — | reviewer repro |
| — | thief #34 B2: `strategy.py` vs `strategy/` collision | BLOCKER | REPORTED, not fixed | — | 47 collection errors |

Reported but NOT fixed (out of this slice's scope, all reproduced by the bug hunter):
BH-02 duplicate-audit ledger desync; BH-05 capture unreachable (police branch is `pass`);
BH-06 league scorer cannot score `timeout`/`tamper_forfeit`, 0-0 series names thief winner;
BH-07 wire turn omits `smell_grid`/`timestamp`, no receive-path validation;
BH-08/OPEN-011 `survival_threshold` dropped by `TERMS_KEYS`, guard unreachable, and
`subgame.py` invents `TECHNICAL_LOSS` at move-cap exhaustion; BH-09 complementary-role
check hard-disabled → same-role pairing deadlocks; BH-11 `Outcome.TIMEOUT` never assigned;
BH-12 series outcome = last sub-game only, `audits_present` hardcoded `True`;
BH-14 malformed opponent input crashes the honest peer; BH-15 capture claim answered
post-move; BH-18 audit_physics off-by-one; BH-19/20/21 dead/stub code.

## E. Final verification (post-fix wave)

| Check | Police | Thief |
|---|---|---|
| `uv run pytest` | **767 passed**, cov 92.40% | **767 passed**, cov 92.07% |
| `uv run ruff check .` | All checks passed | All checks passed |
| `run_quality_gates.py` | 7/7 OK | 7/7 OK |
| focused BH-04 | 3 passed | 3 passed |
| focused BH-10 | 4 passed | 4 passed |
| `git diff --check` | clean | clean |
| `common/` parity | byte-identical across both repos | |

Baselines for contrast: 734 (session start) → 755 (after #32/#33) → **767** (final, on merged masters).

## E2. Independent review

One bounded independent reviewer completed against the merged diffs
(`69e234e..837137f`, `f4af4d9..4b32693`). Verdict: **APPROVE_WITH_NITS — no BLOCKER,
no HIGH.** Fixes 1, 2, 4, 5, 6 assessed clean; fix 3 assessed correct for the bug it
targets. Two earlier reviewer attempts terminated on the account spend limit; only the
third produced a verdict.

Follow-ups it raised (none blocking, none actioned here):
- MEDIUM — `belief/grid.py diffuse()` infers "impassable" from "no mass reached this
  cell", so under `kernel_bayes_v1` (whose multiplier can be 0) a whole non-barrier
  region could in principle be dropped from the allowed mask permanently. Not reachable
  under the default `trust_v1` model, whose multiplier is always >= 1. Suggested fix:
  track barriers in an explicit set rather than inferring exclusion.
- LOW — `belief/update.py apply_half_turn` calls `exclude(barrier)` again after
  `diffuse()`; now a no-op, and its comment is stale.
- LOW, pre-existing — the audit never catches a thief that dishonestly answers
  `claim_response: {"caught": false}` and simply keeps playing without filing a
  `win_claim`. Adjacent to fix 2 but not introduced by it.

Note: the reviewer reported test counts of 815/819; re-measured directly on both merged
masters as **767 passed** each. Use 767.

Real E2E, run 3× (pre-merge, post-scent-lock, post-BH-10): `python -m police_peer` ↔
`python -m thief_peer`, separate OS processes, FastMCP HTTP, 6 sub-games, role
alternation, `audit_ok` all rows, matching `game_uid 6798c086`, both exit 0.
Matching locks accepted; mismatched locks refused with SPAR-N05 before any game state.

**Not verified:** no real counted game, no real Gmail send (both correctly gated).

## F. Not completed

- thief #34 still NEEDS_REWORK — 7 required changes listed on the PR.
- Remote branch deletion — `git push --delete` returns **HTTP 403**; needs a human.
  Provably-merged and safe to delete: `police/18-c06-reporting-league` (`3e9075c`),
  `thief/20-c06-reporting-league` (`c0a983d`),
  `police/task/T016-internal-artifact-contract` (`a4c9033`).
  `police/task/T032` (`314e502`) needs an 8-test spot-check first.
  DO NOT DELETE: `thief/belief-board` (`32fcabc`, sole home of 3 belief-board docs),
  `police/belief-board` (`b3f1de6`, 2 unique ledger edits),
  `police/police-strategy` (`5f7c3bf`, 4,803 lines, no PR).
- `docs/TODO.md`, README, PLAN are materially stale (T006/T010/T028 marked not_started
  though merged; README says "everything above C01 is not started").
- `check_planning_graph.py` fails (3 issues) and is not in CI — the invariant ADR-003,
  ADR-005 and PRD SC-011 claim is verified.
- Issues: 7 open per repo, all mirrored. None closeable on evidence.
- OPEN/PLANQ: 11 OPEN + 8 PLANQ re-audited; patch text prepared for 9 register
  corrections but NOT applied.

## G. Next dependency

Next executable non-strategy task: **fix the `TERMS_KEYS`/OPEN-011 termination seam**
— add `survival_threshold` to the projected terms (or move the divergence check into
config validation) and replace `if terminal is None: terminal = Outcome.TECHNICAL_LOSS`
in `common/transport/subgame.py` with a loud refusal citing OPEN-011. It is
submission-critical, non-strategy, needs no external input, and is reachable today by
the Police peer against any opponent that does not emit a `win_claim`.

True external blockers (narrowed): INPUT-001/002 official templates and submission form;
INPUT-003 Step-0 credential; opponent endpoints (PLANQ-006); team metadata (OPEN-003/010).
None of these block local implementation.
