---
artifact: stage-todo
id: TODO-THIEF-STRATEGY
status: active
version: 0.1
derived_from: PLAN-THIEF-STRATEGY@0.1 · PRD-THIEF-STRATEGY@0.1
applies_to: thief_repo only (role-owned)
owner: orchestrator
updated: 2026-08-21 (stage opened; prerequisites assumed delivered per stage entry criteria — C01 domain+config T003/T004, scent model+lock T005, orchestrator FSM+turn loop T010, MCP transport T009, integrity core T008; belief board T006 is the sibling stage-3 work and an entry criterion for TS-04)
---

# TODO — Thief Strategy (Stage 3, role-specific part)

Task ledger for building the Thief strategy from `PRD_thief_strategy.md` +
`PLAN_thief_strategy.md`. Order follows the PLAN §12 stub-replacement spine: shared core
first, then the evasion policy, then the decision-path swap, then the verification
close-out. **Big-bang integration is not allowed** — the spine test
(`tests/integration/test_series_loopback.py`) must be green after every task, and no task
leaves a new strategy module unwired and untested.

## How this ledger works

- **Status values:** `not started` · `in progress` · `blocked` (names the dependency/gate) ·
  `done` (orchestrator-verified evidence only).
- **Ready rule:** a task is ready when every `depends on` task is `done` and no gate blocks
  start. Two external items gate this stage: (1) the **belief board (T006)** — its ledger
  (`TODO_belief_board.md`) must record G-B3 before TS-04 is claimed; (2) the **PLANQ-008**
  team decision (`TBD_TEAM_DECISION`) — it is `blocks: criterion` on T007's
  `{#heuristics}` acceptance criterion, **not** `blocks: start`: the stage proceeds, and
  only that criterion waits. The PRD §9 values are the approval baseline; the TC-T17
  fixtures are the seeded scenarios it reviews.
- **Responsibility:** `ORC` = orchestrator; `IA` = implementation agent (claims the mapped
  repo task per `AGENTS.md`, edits only its write set, hands off with evidence: files
  changed, tests executed, exact results, decisions, deviations, blockers, newly
  discovered work).
- **Repo mapping:** the repo task file is the claim unit: **T007** (`Implement Role
  Strategy`, write set `src/thief_peer/strategy/` + `tests/unit/strategy/`); **T021**
  absorbs the property-suite + coverage close-out (`tests/property/`). Two ORC-recorded
  write-set extensions are needed before claims (workflow §4: no silent scope expansion,
  the belief stage's FR-B9 recording pattern): (a) `src/thief_peer/wire/__init__.py` for
  the S3 brain swap (stage-2 glue, not in T007's write set); (b)
  `tests/integration/test_strategy_selfplay_kpi.py` for the KPI harness. **T027**
  (optional LLM provider, P2, `optional: true`) stays deferred — PLANQ-003/PLANQ-004
  `blocks: start` on that task only; its `TextProvider` seam is built by TS-02, its
  implementation is not.
- **Cross-repo rule:** the strategy **shared core** (`strategy/decision.py`,
  `strategy/base.py`, `strategy/hints.py`, `strategy/inject.py`, `strategy/__init__.py`)
  must stay mutually consistent with the police-repo counterparts — identical content
  modulo package import path and the role constant (the shared-scent/belief rule). The
  police counterparts are not yet written (planned trio), so until TS-07 the ORC checks
  single-repo internal consistency instead, and the sync check itself is recorded as
  pending.
- **Progress:** the IA updates `status` (and claim fields in the repo task file) while
  working; the ORC verifies evidence before `done`.
- **Spine invariant:** `tests/integration/test_series_loopback.py` green after **every**
  task (PLAN §12 invariant).

## Stage task index

| ID | Task | Phase | Pri | Status | Owner | Depends on | Maps to (repo / PRD) | Gate |
|---|---|---|---|---|---|---|---|---|
| TS-01 | Prerequisites & entry criteria | A | P0 | not started | ORC | — | T004/T005/T008/T009/T010 assumed · T006 (belief) · write-set extensions | G-T0 |
| TS-02 | Shared core: `Decision`, `BrainBase`, `HintWriter`, injection seam | B | P0 | not started | IA | TS-01 | T007 · FR-T1 (partial), FR-T6, FR-T7, FR-T9, FR-T11 | G-T1 |
| TS-03 | `ThiefBrain`: scored evasion, threat fallback, visited | B | P0 | not started | IA | TS-02 | T007 · FR-T2, FR-T3, FR-T4, FR-T8 | G-T1 |
| TS-04 | Spine swap: `BrainDrivenEngine` in the glue (S3a/S3b/S3c) | C | P0 | not started | IA | TS-03 (+ T006 G-B3, write-set extension recorded) | T007 · PLAN §12, SD-T4, SD-T7 | G-T2 |
| TS-05 | Verbal hardening: isolation, verdict rule, cap, lie rate | C | P0 | not started | IA | TS-03 | T007 · FR-T6, FR-T7, TC-T09…T11 | G-T2 |
| TS-06 | KPI self-play + property + determinism + perf + coverage close-out | D | P1 | not started | IA | TS-04, TS-05 | T007 + T021 · PRD §2.3 KPIs, NFR-1/2 | G-T3 |
| TS-07 | Shared-core cross-repo sync + docs sync | D | P1 | not started | ORC | TS-06 + police counterparts (not yet written) | — · Goal 6, NFR-6 | G-T3 |

## Phase A — Prerequisites

### TS-01 — Prerequisites & entry criteria (owner: ORC)

- [ ] Verify the stage entry assumptions hold on the integration branch: C01 domain +
  config (T003/T004), scent model + lock (T005), orchestrator FSM + turn loop with
  stand-in engine (T010), MCP transport + turn frames (T009), integrity core (T008).
- [ ] Confirm the belief stage's G-B3 is recorded in `TODO_belief_board.md` (real
  `BeliefGrid` live in the turn handler, spine green) — the entry criterion for TS-04.
- [ ] Record the two write-set extensions in `docs/tasks/` **before** claims (workflow
  §4): (a) `src/thief_peer/wire/__init__.py` (S3 brain swap); (b)
  `tests/integration/test_strategy_selfplay_kpi.py` (KPI harness).
- [ ] Confirm T007 is `ready` in the repo ledger (depends_on T004, T006 done) and note
  that PLANQ-008 (`TBD_TEAM_DECISION`, `blocks: criterion`) does **not** block the claim;
  the PRD §9 values are the approval baseline for it.

**Verification:** ORC checklist with branch/commit references. **DoD:** G-T0 passed.

## Phase B — Shared core and the policy

### TS-02 — Shared core: `Decision`, `BrainBase`, `HintWriter`, injection seam (owner: IA → repo task T007)

- `strategy/decision.py`: frozen `Decision` dataclass, field invariants (PRD §5.3 table).
- `strategy/base.py`: `BrainBase` — pinned two-phase `decide()` (move → hint; forced-STAY
  path with `fallback=True`), `reset(start)` (visited = `{start}`, `last_field = {}`),
  `note_evidence(field)` (SD-T4), `visited` update on orthogonal MOVE only (FR-T8).
- `strategy/hints.py`: `HintWriter` — role-parameterized template banks (3–4 truth/lie
  variants each), seeded lie roll ≈ 0.4, verdict rule-computed (contains or
  Chebyshev-adjacent ⇒ "truth"), generic non-landmark fallback line, `_cap` to
  `hint_max_words`; `TextProvider` Protocol seam (SD-T5 — seam only, no adapter).
- `strategy/inject.py`: `resolve_brain_cls` (fail-fast `ValueError`/`TypeError`),
  `resolve_brain` (seeded construction; per-sub-game role, FR-T9).
- `strategy/__init__.py`: public re-exports.
- Unit tests TC-T01, TC-T12, TC-T14 (partial: import scan), TC-T10 (partial: phase order).

**Verification:** `uv run pytest tests/unit/strategy -q`; `uv run ruff check
src/thief_peer/strategy tests/unit/strategy`; line cap check. **DoD:** G-T1 — shared core
constructible with zero model/network dependencies; the seam fail-fast behavior proven;
template hints generate offline.

### TS-03 — `ThiefBrain`: scored evasion, threat fallback, visited (owner: IA → repo task T007)

- `strategy/thief.py`: `ThiefBrain` — `_threat` (FR-T2 chain: peak above
  `min_confidence` → `hottest(last_field)` → board centre), `_decide_move` (FR-T3 score
  formula, first-maximum tie-break in CT-01 order, `(action, None)` — never a barrier,
  FR-T4), weights from the `[strategy.thief]` config mapping (PRD §9).
- Unit tests TC-T02 (unit level), TC-T03 (all three threat branches, boundary included),
  TC-T04, TC-T05, TC-T06, TC-T07, TC-T08, TC-T13; A/B fixtures for MS-3 (swapped belief
  peak vs. uniform belief ⇒ different actions in the evasion fixtures).

**Verification:** `uv run pytest tests/unit/strategy -q`; ruff; line cap. **DoD:** G-T1
complete — the policy is deterministic and legal by construction; belief demonstrably
changes selection (MS-2/MS-3 fixtures).

## Phase C — The loop and the verbal layer

### TS-04 — Spine swap: `BrainDrivenEngine` in the glue (owner: IA → repo task T007, write-set extension recorded)

- `src/thief_peer/wire/__init__.py`: `BrainDrivenEngine` implementing the existing
  `TurnEngine` seam (PLAN §12 S3a): fresh `GameEngine` per sub-game (C01, as today);
  THIEF sub-games: `resolve_brain(config, role)` + `brain.decide(state, belief,
  opponent_hint, arena)` + `engine.apply_own_move(action)`; POLICE sub-games: the
  stand-in selection is kept on the existing path, labeled (SD-T7).
- S3b: the outgoing frame's hint comes from `Decision.hint` (template writer), replacing
  the canned `"I am here"`.
- S3c: `brain.note_evidence(smell_grid)` on each received turn, before the decision
  (SD-T4).
- Spine run with the real belief (belief stage S1/S2 already wired) and the real Thief
  brain; TC-T18.

**Verification:** `uv run pytest tests/integration/test_series_loopback.py -q` green with
the real brain on Thief sub-games; `uv run pytest tests/unit/strategy -q`; ruff; line cap.
**DoD:** G-T2 — the decision path is brain-driven end-to-end over loopback, full
six-sub-game series settles, no stand-in decision left on the Thief path.

### TS-05 — Verbal hardening: isolation, verdict rule, cap, lie rate (owner: IA → repo task T007)

- TC-T09 full (word cap, landmark naming, verdict domain, seeded lie fraction
  0.30–0.50 over 1000 hints, deterministic per seed).
- TC-T10 full (boom hint writer / boom provider never change the action; a slow or failed
  provider ⇒ template fallback with the action unchanged — CT-02 failure behavior;
  NG-003: no consultation on the move path).
- TC-T11 (verdict recomputed independently from position + asserted landmark region ⇒
  matches the sealed verdict on every generated hint).

**Verification:** `uv run pytest tests/unit/strategy -q`; spine still green; ruff; line
cap. **DoD:** G-T2 complete — the verbal layer is bounded, isolated, and audit-consistent
(M-04 `{#hint_isolation}` proven).

## Phase D — Verification close-out

### TS-06 — KPI self-play + property + determinism + perf + coverage close-out (owner: IA → repo task T007 + T021, write-set extension recorded)

- `tests/property/strategy/` (T021 write set): TC-T02 full — 10k random seeded
  (engine, belief, field) fixtures ⇒ action in the legal set, `barrier_cell` `None`,
  `fallback` flag exact.
- `tests/integration/test_strategy_selfplay_kpi.py` (extension recorded in TS-01): TC-T17
  — 200 seeded games, role-pinned Thief sub-games, shipped config: survival vs the
  reference `PoliceBrain` test double ≥ 60%; vs the stage-2 stand-in selection ≥ 30%
  (labeled; re-measured vs the designed police brain when the police stage lands); median
  rounds-to-capture ≥ 22. The reference baseline brain lives in the harness as a test
  double (registered evidence, non-authoritative).
- Determinism TC-T15 (two runs, same seed + same wire transcript ⇒ byte-identical
  decision logs); perf TC-T16 (≤ 10 ms p99 over 10k iterations).
- Coverage to ≥ 85% on `strategy/`; docs sync: M-04 cross-link to the stage docs, C02
  PLAN note, stage-3 index in `docs/` (orchestrator).

**Verification:** full command set of PLAN §15 in the thief repo; ORC evidence review.
**DoD:** G-T3 close-out candidate — KPI numbers recorded, property suite green,
determinism/latency inside budget.

### TS-07 — Shared-core cross-repo sync + docs sync (owner: ORC)

- Once the police counterparts exist (planned trio in `police_repo/docs/`): the ORC
  sync-checks `strategy/{decision,base,hints,inject,__init__}.py` — identical content
  modulo package import path and the role constant (the cross-repo rule); TC-T19.
- Confirm the "shared core" sections of `PRD/PLAN/TODO_thief_strategy.md` and their police
  mirrors are mutually consistent (same schema, same invariants, same wording modulo role
  words); record G-T3 evidence; reconcile T007/T021 state in `docs/TODO.md`.

**Verification:** sync check output + ORC evidence review in both repos. **DoD:** G-T3
passed — stage done.

## TC coverage progression

| After | Unit | Property | Integration (spine) | KPI/Perf/Determinism |
|---|---|---|---|---|
| TS-02 | TC-T01, T10(p), T12, T14(p) | — | baseline green | — |
| TS-03 | + TC-T02 (unit), T03, T04, T05, T06, T07, T08, T13 | — | green | — |
| TS-04 | + TC-T18 | — | S3a/S3b/S3c wired, green | — |
| TS-05 | + TC-T09, T10, T11 full | — | green | — |
| TS-06 | all | TC-T02 full (10k) | green | TC-T15, T16, T17 |
| TS-07 | — | — | green | TC-T19 (sync check) |

## Stage definition of done (G-T3)

- [ ] MS-1…MS-5 of PRD §2.2 each have recorded evidence (test names + results).
- [ ] All TC-T## pass in the thief repository; coverage ≥ 85% on `strategy/`; ruff clean;
  no file over the 150-line cap; no new dependencies; no secrets.
- [ ] Spine green with the real `ThiefBrain` on the Thief decision path; opposite-role
  sub-games on the stand-in with SD-T7 recorded (full six-sub-game series settles).
- [ ] KPI numbers recorded from 200 seeded games: ≥ 60% survival vs the reference
  `PoliceBrain`; ≥ 30% (vs the stand-in, labeled); median rounds-to-capture ≥ 22.
- [ ] PLANQ-008 baseline values (PRD §9) flagged for the team decision; the `{#heuristics}`
  criterion is checkable once approved (not blocked meanwhile).
- [ ] Shared core internally consistent and role-parameterized only by import path / role
  constant; cross-repo sync check recorded as pending until the police counterparts exist
  (TS-07 owns it).
- [ ] Orchestrator has reconciled T007/T021 state in `docs/TODO.md` and recorded the G-T3
  evidence in the task files.

## Relationship to the Repository Documents

- **Upstream:** `docs/PRD_thief_strategy.md` + `docs/PLAN_thief_strategy.md` (this
  stage's PRD/PLAN — the TC/SD/MS IDs in this ledger are theirs); M-04 (the binding
  mechanism contract); T007 (the claim unit; PLANQ-008 `blocks: criterion` on
  `{#heuristics}`, not a start blocker).
- **Siblings (same stage, separate files):** the belief trio
  (`docs/PRD_belief_board.md` + `PLAN` + `TODO`) — T006's G-B3 is the entry criterion
  for TS-04; the planned police trio (`police_repo`) — the counterpart of the shared-core
  sync check (TS-07).
- **Execution:** this ledger's tasks map to T007 (claim unit; write-set extensions for
  the glue swap and the KPI harness are ORC-recorded in TS-01) + T021 (property/coverage
  close-out); T027 stays deferred and gated (PLANQ-003/PLANQ-004). The global
  `docs/TODO.md` is reconciled by the orchestrator after each wave; this ledger does not
  edit it.
- **Assumed delivered (stage entry criteria):** C01 domain + config (T003/T004), scent
  model + lock (T005), orchestrator FSM + turn loop (T010), MCP transport + turn frames
  (T009), integrity core (T008).
