---
artifact: stage-prd
id: PRD-THIEF-STRATEGY
status: draft — pending orchestrator approval (workflow step 5, guidelines p. 9 §2.5)
version: 0.1
derived_from: PRD-FINAL-P2P@0.5 · M-04-thief-strategy · PRD-BELIEF-BOARD@0.1
canonical_requirements: ARCH-007, STRAT-007, STRAT-008, STRAT-009, GAME-012, SEC-007
applies_to: thief_repo only (role-owned). The marked "shared core" sections mirror
  police_repo/docs/PRD_police_strategy.md and must stay in sync
owner: orchestrator
source_spec_version: "3.0.0"
updated: 2026-08-21
---

# PRD: Thief Strategy — Evasion Decision Policy Under Partial Observation

## 1. Overview & Context

### 1.1 Purpose

The thief strategy is the decision policy of the Thief peer: on every own turn it selects
exactly one legal action from this peer's own local state (CT-01) and the belief board's
snapshot of the hidden Police position (M-02 — specified in `docs/PRD_belief_board.md`, the
sibling shared part of this stage), and only afterwards produces the outgoing verbal hint
(template mode by default). The policy exists to keep the Thief alive past the survival
threshold (step ≥ 35, signed) while the Police pursues a belief peak, places up to 14 public
barriers (GAME-008), and can end the game from its own side of the board (rules 46/47 —
visible only to the Thief).

This is the **role-specific part** of the Stage-3 Perception & Strategy work. The belief
board (the inference half) is identical in both role repositories and is specified
separately in `docs/PRD_belief_board.md`; the policy that consumes it is role-specific and
lives here (Thief) and in `police_repo/docs/PRD_police_strategy.md` (Police, planned). The
**shared core** of the strategy module — the `Decision` contract, the `BrainBase` phase
discipline, the verbal `HintWriter`, and the injection seam — is specified in the clearly
marked shared-core sections below (FR-T6, FR-T7, FR-T9 and the §5 output table) and must stay
mutually consistent between both role documents; the ORC sync-checks it after every wave, the
same rule that applies to the shared scent and belief modules.

This PRD decomposes the approved product contract for the Thief strategy and implements the
mechanism PRD `docs/mechanisms/M-04-thief-strategy.md` (binding) and the shared C02 component
PRD. It makes the policy compatible with the **adopted operational interoperability profile**
(ADR-004: `wire_shape` `reference-v3`, scent `subtractive_chebyshev_v1` default, `info_mode`
belief) — the strategy's *output* is private (no cross-team byte agreement on moves or hints,
SPEC §1), but the wire fields the decision flows into must respect the pinned surface (§10).

**Stage numbering note (stated once).** Book ch. 10 splits stage 3 ("blind strategy") from
stage 4 ("language and scent"). This project folds them: the scent model (book stage 4) was
delivered early (T005), so this single Stage 3 delivers the strategy module on top of a
working scent + belief pair. The belief half is the sibling shared trio
(`PRD/PLAN/TODO_belief_board.md`); this document is the strategy half.

**Prerequisites (assumed delivered, per stage entry criteria).** Base board + domain rules +
config (C01, T003/T004); scent model + lock (T005); orchestrator state machine + turn loop
(T010); MCP transport + turn frames (T009); integrity core (T008). The stage-2 role glue
carries a **stand-in decision engine** (PLAN-MCP-INFRA SD-03: `legal_moves[0]` + a canned
hint) that this stage replaces on the decision path. The belief board (T006) is the sibling
stage-3 work and is an entry criterion for the spine swap (TODO TS-04).

### 1.2 Problem Statement

Each peer knows only its own position (STRAT-001). The Thief never sees the Police; what it
can use each turn is:

- the **belief snapshot** about the Police position — `most_likely()`,
  `peak_probability()`, `top_k()`, `prob(cell)` (PRD-BELIEF-BOARD FR-B6);
- the **last received scent field** (raw channel, decaying and stale, `hottest()` helper of
  the delivered scent module) — for fallback when the belief is too diffuse to trust;
- the **public barrier list** (exact, truthful, GAME-012) — barriers are impassable to both
  and can end the game: a barrier on the Thief's own cell (rule 46) or a cell with no legal
  orthogonal move (rule 47) is a capture the *Thief* must observe.

The policy must therefore:

- Select **only from the CT-01 legal-action set** (orthogonal moves in fixed order, then
  `STAY`); it never invents an action (M-04 `{#evasion_legality}`).
- Move **away from where the Police is believed to be** (book ch. 6 §6.4: the cop minimizes
  Manhattan distance to the belief peak; the thief maximizes it).
- **Preserve future mobility** — the reference distance-max baseline (report §5.2) walks the
  Thief into corners: maximal distance, zero escape options, and a trap the Police is one
  barrier away from sealing (rule 47). Mobility and trap terms fix that without lookahead.
- **Grow the visited set** — the signed `network_and_league.diversity_reward` (10, in the
  signed `game.json`) rewards unique cells at series scoring; a freshness term is the
  per-decision proxy for it (the reference Thief's second key already prefers unvisited
  cells, report §5.2).
- **Fall back sensibly when the belief is diffuse** — a peak with probability below a
  confidence floor is a noisy point estimate; the policy degrades to the raw scent channel,
  then to the board centre, so `decide()` is total (it never has no target).
- Stay **deterministic** (same seed + same wire transcript ⇒ identical decisions) and
  **fast** (move selection is instant and free of any model call, book ch. 6 §6.2/§6.5).
- Produce a hint that is **free natural language** (NET-003/NET-004), arena-bounded, within
  the signed word cap, **truthful or deceptive** (STRAT-009), and **isolated from movement**
  (M-04 `{#hint_isolation}` — a hint can never influence an already-selected move).
- **Never touch the capture-claim answer** — during a Capture Claim the Thief must answer
  truthfully (SEC-007, M-04 `{#capture_response_honesty}`); that answer is computed by the
  domain (`GameEngine.answer_capture_claim`) and sealed by C03. The policy consumes it as a
  hard boundary: it has no field for it and no path to it.

### 1.3 Theoretical Background

The setting is a decentralized partially observable stochastic game (Dec-POMDP, book ch. 6
§6.4): the Thief's policy is a function of its belief state and own local state, never of the
global state. The belief board (PRD-BELIEF-BOARD) is a grid-based Bayesian filter over the
cell set; this PRD is the **policy** on top of it — a deterministic ranking over the legal
action set.

**Evasion as a multi-criterion ranking.** With the shipped orthogonal move set, Manhattan
distance is the admissible step estimate (book ch. 6 §6.4, `D = |xc−xt| + |yc−yt|`); the
policy scores every legal action's destination on four terms (all O(1) per action — no
lookahead, book §6.3.1's "your own heuristic algorithm" route):

1. **Distance** — maximize Manhattan distance from the destination to the *threat cell*
   (the believed Police position; the threat-selection rule in FR-T2). The primary evasion
   term; the book's symmetric recipe (cop minimizes, thief maximizes).
2. **Mobility** — maximize the number of legal orthogonal options *from the destination*.
   Pure distance-max optimizes one step and dies on the next: a corner is the global maximum
   of distance and the global minimum of mobility. This is the term that makes the rule-47
   trap avoidable one step before it is fatal.
3. **Freshness** — prefer destinations never visited this sub-game (role-local `visited`
   set, FR-T8). Diverse movement keeps the Police's belief diffuse (a fleeing thief that
   loops in place is easy to pin down) and feeds the signed diversity reward.
4. **Trap-risk penalty** — a destination with at most one orthogonal exit (`trap_risk`,
   `orthogonal_mobility(dest) <= 1`) is penalized hard enough that no combination of the
   other terms can select it while a non-trap-risk alternative exists. This is a conservative
   strategy-level policy heuristic, not the domain's rule-47 terminal predicate
   (`Board.boxed_in`, all four neighbours blocked): after any legal move from a reachable
   non-terminal state the vacated origin remains an unblocked neighbour, so `boxed_in` is
   never true of a legal destination — it stays the domain's own capture check, unchanged.
   `trap_risk` instead flags a destination one further barrier could seal, without claiming
   the destination is itself a capture.

The weighted sum with config-owned weights (PRD §9) is **derived design / project
convention**, not an official requirement: M-04 marks the evasion priority ordering as
"derived design, not an official requirement", and PLANQ-008 (`TBD_TEAM_DECISION`) records
the approved heuristic priorities and seeded scenarios. The values in §9 are the baseline
that PLANQ-008 approves or revises; the task proceeds in the meantime (`blocks: criterion`,
not `blocks: start`).

**The three movement-policy routes** (book ch. 6 §6.3/§6.3.1, presented as equal citizens):
(1) pure Bayes + Manhattan heuristics — the reference default; (2) "your own heuristic
algorithm" — richer deterministic policy; (3) RL (Q-learning, Bellman updates, ε-greedy) —
explicitly optional and not taught in the course. This stage implements route (2): the
scored heuristic of the four terms above, with route (1) kept as the A/B baseline in the KPI
harness (report §10: "replacing it is the assignment"). RL and lookahead remain P2 options
(STRAT-007 says none is required).

**The verbal layer** (book ch. 6 §6.5/§6.5.1) is separated from space by the same module
boundary (ARCH-007): the LLM — if configured at all — writes text only; the move is chosen
entirely by pure Python ("space → algorithm, words → (optional) LLM", report §1). The
recommended default is the zero-token **template** mode (STRAT-008 SHOULD; book §6.5.1's four
provider tiers: template → ollama → claude_api → claude_cli; an optional provider adapter is
T027, P2, and out of scope for this stage — only the provider-neutral seam is defined).
Hints may lie (STRAT-009 MAY): the template Thief asserts its own location using the arena's
landmark names and lies with probability ≈ 0.4 through the seeded RNG (reference behaviour,
report §5.4), naming a landmark it is not near; the sealed `verdict` ("truth"/"lie") is
computed locally from the role's own position, so it is always well-defined and auditable.

### 1.4 Target Audience

The peer runtime (C04 turn loop — calls `decide()` once per own turn and applies the result),
C03 (seals the decision's commit fields — move, verdict, prompt text — into the per-step
commit chain, SPEC §3), the test suite (property tests for legality, KPI self-play harness,
determinism/latency), the project team (approval baseline for PLANQ-008), and the evaluator
(audits against M-04's acceptance scenarios). The Police strategy document
(`police_repo/docs/PRD_police_strategy.md`, planned) reads the shared-core sections as its
mirror.

## 2. Goals & Success Metrics

### 2.1 Goals

1. One deterministic Thief policy in `src/thief_peer/strategy/` that selects only from the
   CT-01 legal set and never places a barrier (M-04 `{#evasion_legality}`, role guard).
2. The policy consumes the belief board and **materially influences** selection (STRAT-006)
   — peak-following evasion when confident, scent fallback when diffuse, demonstrated by
   fixtures and by the KPI harness.
3. Zero-token template hints by default, isolated from movement (STRAT-008, M-04
   `{#hint_isolation}`); a slow or failing text generator can never block or select the move
   (CT-02 failure behavior).
4. The stand-in decision engine (PLAN-MCP-INFRA SD-03) is replaced by the real brain on the
   decision path with the spine green after every swap (PLAN §12).
5. Determinism: same seed + same wire transcript ⇒ byte-identical decision logs; decision
   latency p99 ≤ 10 ms on the shipped 7×7 board.
6. The shared-core files (`strategy/decision.py`, `strategy/base.py`, `strategy/hints.py`,
   `strategy/inject.py`, `strategy/__init__.py`) remain mutually consistent with the Police
   repo's counterparts modulo package import path and the role constant (shared-code rule).

### 2.2 Success Criteria (Milestones)

| ID | Milestone | Evidence |
|---|---|---|
| MS-1 | Shared core built | `Decision`, `BrainBase`, `HintWriter`, injection seam constructible and unit-green: TC-T01, TC-T12, TC-T14 (partial) |
| MS-2 | Evasion policy built | `ThiefBrain` unit-green: TC-T02 (unit level), TC-T03…T08, TC-T13 |
| MS-3 | Belief materially influences selection | TC-T03 (all three threat branches) + A/B fixtures: same brain, swapped belief peak vs. uniform belief ⇒ different actions in the evasion fixtures; confident belief ⇒ away-from-peak behaviour |
| MS-4 | Real brain in the loop | Spine swap (PLAN §12 S3a/S3b/S3c): TC-T18 — `tests/integration/test_series_loopback.py` green with the real Thief brain on Thief sub-games |
| MS-5 | KPI + determinism close-out | TC-T15, TC-T16, TC-T17 pass; coverage ≥ 85% on `strategy/` |

### 2.3 KPIs

Project-set (not official) targets, measured by a seeded self-play harness (role-pinned Thief
sub-games, shipped 7×7 config):

| KPI | Target |
|---|---|
| Thief survival vs reference `PoliceBrain` (200 seeded games) | ≥ 60% |
| Thief survival vs this project's police brain (same harness) | ≥ 30% — re-measured when the police stage lands; until then measured against the stage-2 stand-in selection (labeled as such) |
| Thief median rounds-to-capture when captured | ≥ 22 |
| Illegal actions across 10k fuzzed `decide()` calls (property test) | 0 |
| Decision latency p99 (Thief `decide()`, 7×7, CPython 3.12) | ≤ 10 ms |
| Determinism: two runs, same seed + same wire transcript | byte-identical decision logs |
| Coverage on `strategy/` / line cap / ruff | ≥ 85% / 0 files over 150 / clean |

## 3. Functional Requirements

### FR-T1 — Legal-set-only selection (M-04 `{#evasion_legality}`, CT-01, STRAT-001)

The policy iterates exactly the CT-01 legal list — orthogonal moves in the fixed `N, S, W, E`
order, `STAY` last (`Board.legal_moves`) — and returns one member of it; it never invents an
action, never outputs a barrier, and never depends on the opponent's true position. When the
legal list is exactly `["STAY"]` (all orthogonal moves blocked), the policy returns
`("STAY", None)` with `fallback=True`; whether that state is a capture (rule 47) is decided
by the domain's `GameEngine.self_captured()`, not by the policy.

### FR-T2 — Belief-driven threat selection with diffuse fallback (STRAT-006)

The evasion target ("threat") per turn is, in fixed order:

1. `belief.most_likely()` when `belief.peak_probability() >= min_confidence` (private config,
   default 0.15) — confident belief ⇒ chase its peak;
2. else `scent.hottest(last_received_field)` (delivered scent-module helper, lexicographic
   tie-break) — diffuse belief ⇒ the raw scent channel;
3. else the board centre — empty field ⇒ the decision is still total.

The distance term (FR-T3) is then maximized against that threat. The fallback chain keeps
`decide()` total and keeps the policy honest about its own uncertainty: a diffuse peak is a
noisy point estimate, not a fact.

### FR-T3 — Scored multi-criterion ranking, deterministic tie-break
**(derived design — M-04 "derived design, not an official requirement"; PLANQ-008)**

Each legal action's destination is scored (weights from private config §9):

```
score = w_dist * manhattan(dest, threat) / board.size
      + w_mob  * mobility(dest) / 4
      + w_fresh * fresh(dest)
      - w_trap * trap(dest)

mobility(dest) = number of legal orthogonal moves from dest (len(legal_moves(dest)) - 1)
fresh(dest)    = 1 iff the action is an orthogonal MOVE and dest not in visited
trap(dest)     = 1 iff trap_risk(dest) := orthogonal_mobility(dest, barriers) <= 1
```

`trap_risk` is a strategy-level policy predicate, distinct from `Board.boxed_in` (the domain's
rule-47 zero-exit terminal check, unchanged): it conservatively flags a reachable destination
with at most one orthogonal exit, not a guaranteed capture.

The winning action is the **first maximum** in CT-01 order (strict greater-than comparison
while scanning) — deterministic tie-break, the reference's own convention (report §5.2).
`w_trap` (default 5.0) dominates the maximum possible non-trap-risk score (≤ 1.0 + 1.71·1.0 +
0.25 + 0.15 < 3.2), so a trap-risk destination is never selected while any lower-risk
alternative exists. The priorities and weights are the PLANQ-008 approval baseline (PRD §9),
not an official requirement.

### FR-T4 — Role guard: the Thief never places a barrier (M-04 role-specific, GAME-012)

`Decision.barrier_cell` is always `None` for the Thief role, regardless of config. The
domain enforces the same rule (`GameEngine.place_own_barrier` raises for non-Police); the
policy layer must not even reach for it. The Thief consumes the *declared* barrier list as
public truth (mobility and trap inputs) — barriers are exact and truthful by rule (GAME-012).

### FR-T5 — Truthful capture response is outside the policy's path (SEC-007, M-04 `{#capture_response_honesty}`)

The Capture Claim answer — `{"claim": [r,c], "caught": bool}` — is computed by the domain
(`GameEngine.answer_capture_claim`, Thief-only) and sealed by C03. It is **always truthful**:
a false denial is provable at audit against the sealed state string and disqualifying. The
policy implements no part of it: `Decision` has no claim field, and no policy method reads
or writes one. The policy's only obligation is the negative one — never interfere with that
path (e.g., never gate or delay the game-ending final on policy grounds).

### FR-T6 — Verbal hint: template default, arena-bounded, capped, declared verdict
**(STRAT-008, STRAT-009 — shared core, mirrors the Police role doc)**

- `HintWriter(role, rng, arena, max_words)`; **template mode is the default** — zero tokens,
  fully offline, the book-recommended route (book §6.5.1; STRAT-008 SHOULD).
- Template line banks per role (3–4 truth/lie variants each) in the shared core; hints
  **assert the speaker's own location** using landmark names **imported from
  `belief.hints.LANDMARK_CELLS`** (SD-B3 of PLAN-belief-board — one table, both directions;
  never a copy). The receiver's belief board interprets an incoming hint as a claim about the
  sender, which is why this composition works end-to-end.
- The template lies with probability ≈ 0.4 through the **seeded** RNG (reference behaviour):
  a lie asserts a landmark region the role is not in (and not Chebyshev-adjacent to). If no
  landmark region contains or is Chebyshev-adjacent to the position, the truth branch falls
  back to a generic non-landmark line (no claim, verdict "truth").
- The **verdict is computed locally**: `"truth"` iff the asserted landmark region contains
  (or is Chebyshev-adjacent to) the role's actual position — the role knows its own position,
  so the verdict is well-defined for both roles and always matches the sealed audit record.
- Output is truncated to `hint_max_words` (signed, shipped 15) by `_cap`; for LLM providers
  (T027) the arena and the cap also go into the system prompt (reference behaviour).
- Hints are free-form natural language (NET-003) — never a disguised coordinate (NET-004).

### FR-T7 — Hint isolation and LLM exclusion from movement
**(M-04 `{#hint_isolation}`, NG-003, CT-02 failure behavior — shared core)**

The phase order is **pinned** in `BrainBase.decide()`: **move first, hint second** — the hint
can never influence an already-selected move. `_decide_move` is pure Python and the LLM is
**never consulted** on the movement path (NG-003: an LLM must not bypass deterministic
legality; book ch. 6 §6.5 warning box). Any optional provider call that is slow, fails, or
returns unparseable text falls back to the template **without touching the already-selected
action** (CT-02 failure behavior; book §6.5.1 deadline + fallback), so banter can never stall
the game.

### FR-T8 — Role-local visited set for the freshness term (derived design, M-04 split)

`BrainBase` owns `visited: set[Cell]` — initialized to `{start}` per sub-game, a destination
added **only on an orthogonal MOVE** (not `STAY`), never serialized, never sent, reset on
sub-game start. This repo's `GameEngine` has no visited set, but the freshness term (FR-T3)
and the diversity reward need it; it is role-local evidence, not opponent truth, so it
respects STRAT-001/OBS-002.

### FR-T9 — Injection seam: config-selected brain, fail-fast
**(ARCH-007, book ch. 6 §6.2 — shared core)**

- Private config `[strategy] thief_class` (and `police_class` in the mirror) carries an
  optional dotted `"package.module:ClassName"` selector; `resolve_brain_cls(config, role)`
  is **fail-fast**: `ValueError` on a malformed selector or missing attribute, `TypeError` if
  the target is not a `BrainBase` subclass.
- `resolve_brain(config, role, llm, rng)` instantiates the resolved class with the seeded
  RNG (default: the resolved config's seed), the arena, the signed word cap, and the
  template `HintWriter`. The C04 runtime **never hard-codes** a brain (reference
  `runtime.py` L73 pattern; book §6.2: the module is chosen in the private config's
  `[strategy]` section). With `[strategy]` unset, the shipped role brain of this stage runs
  — Thief sub-games run `ThiefBrain`; the opposite-role default is recorded in PLAN SD-T7.
- The brain is resolved **per sub-game role** (roles alternate across the series,
  `role_for`), so the seam takes the played role, not the peer's natural role.

### FR-T10 — Determinism and seeding discipline (STRAT-007, NFR-2)

Every decision is a pure function of (engine state, belief snapshot, last received field,
config, seed-derived RNG stream). No wall clock and no environment read enter the decision
(`response_seconds` is measured metadata, not an input). Given an identical sub-game wire
transcript and seed, two runs produce byte-identical decision logs (action, hint, verdict,
fallback at every step).

### FR-T11 — No hidden-truth leakage (STRAT-001, OBS-002)

No constructor, method, or field of any strategy module accepts the opponent's actual
position, the opponent's role-internal state, or any value only derivable from them. The
evidence surface is: CT-01 local state, the belief snapshot (already a pure inference
product), the received scent field, the received hint text, the public barrier list, the
signed config. A static test (mirror of belief TC-B12) asserts no import of opponent-truth
symbols into `strategy/`.

### 3.1 User stories

- **As the runtime**, I call `decide(engine, belief, last_hint, arena)` once per own turn and
  get back a legal action plus a hint in microseconds — the LLM's availability is not part
  of my timing.
- **As the auditor**, I can recompute the sealed `verdict` from the role's own revealed
  position and the asserted landmark, and I can prove the move phase never saw the hint.
- **As the evaluator**, I can point at M-04's three acceptance scenarios
  (`{#evasion_legality}`, `{#capture_response_honesty}`, `{#hint_isolation}`) and at the
  property tests that prove each, without reading the Police code.
- **As the Police peer across the wire**, I receive hints that may be lies and scent that
  cannot — and my belief board (the mirror of this policy's evidence) does the rest; nothing
  this policy emits is a numeric position.

## 4. Non-Functional Requirements

### NFR-1 — Performance

`decide()` (both phases, template mode) ≤ 10 ms p99 on a 7×7 board, CPython 3.12, laptop
class CPU. The scoring loop is ≤ 5 destinations × O(1) queries (`legal_moves` from a cell is
itself O(1) on 7×7); the hint phase is a table lookup and a word cap. An optional provider
call (T027, out of scope) is deadline-bounded outside this budget by CT-02's failure
behavior.

### NFR-2 — Determinism

Identical inputs ⇒ identical outputs, every run (FR-T10). No wall clock, no dict-order
dependence beyond the pinned CT-01 action order and sorted/seeded iteration where order
matters, no hash-seed dependence. The lie roll and any other stochasticity run on the
injected seeded RNG only.

### NFR-3 — Testability

The module is testable with plain data (no transport, no config file on disk): config arrives
as constructor arguments, the belief and the engine arrive as objects. Property tests drive
it with random-but-seeded (engine, belief, field) fixtures; the KPI harness drives it over
the delivered loopback spine with a reference-baseline opponent (test double, not the real
Police peer).

### NFR-4 — Configurability

Adjustable values live in private config only: `[strategy]` (selector) and
`[strategy.thief]` (weights, thresholds — §9). Shared signed values (board size, move set,
barrier quota, move cap, survival threshold, arena, word cap, diversity reward) are consumed,
never overridden. Private config can never weaken a signed value (CFG-006 precedence: on any
key conflict the shared JSON overlays the private TOML).

### NFR-5 — Security and separation

No secrets, no credentials, no environment reads in `strategy/`. No import path may reach
the opponent's local truth (FR-T11's static test) or the network layer. The optional
provider (T027) is isolated behind the `TextProvider` Protocol and the Gatekeeper (SEC-009
token metering is C03/C06 territory, consumed not computed here).

### NFR-6 — Modularity and dependency discipline

`strategy/` depends only on `common.domain` (Board geometry, `Cell`, `manhattan`,
`GameEngine`, `Role`), `thief_peer.belief` (snapshot queries + the `LANDMARK_CELLS` table,
SD-B3 import) and `thief_peer.scent` (the `hottest` helper) — nothing else: not the wire,
not the transport, not the GUI. The shared-core files are identical in both role repositories
modulo package import path and the role constant (the shared-scent/belief precedent); the
ORC sync-checks after every wave that touches them. Files stay under the 150-line cap; no
speculative abstractions (one frozen dataclass, one base class, one writer, one seam, one
role brain).

## 5. Expected Input / Output

### 5.1 Input (per sub-game construction)

| Input | Source | Notes |
|---|---|---|
| own role for the sub-game + start cell | CT-01 / `role_for` (signed starts) | brain is reset per sub-game: `visited = {start}`, `last_field = {}` |
| board (signed size 7) | CT-01 / shared game.json | geometry only; the policy never forks it |
| private `[strategy]` / `[strategy.thief]` config | private game.toml | §9; selector + weights |
| arena (`world.map_area`, shipped "New York") + `hint_max_words` (signed 15) | shared game.json | hint content bounds (STRAT-009) |
| seed | resolved private config | the injected `random.Random` (FR-T10) |

### 5.2 Input (per own turn, to `decide()`)

| Input | Source | Notes |
|---|---|---|
| `state: GameEngine` | CT-01 local state | `legal_moves()`, `position`, `barriers`, `board` — own truth + public barriers only |
| `belief: BeliefGrid` snapshot | PRD-BELIEF-BOARD FR-B6 (via the C04 turn loop) | `most_likely()`, `peak_probability()`; read after the turn's update |
| last received scent field | CT-03 `smell_grid` (via the C04 `note_evidence` hook, PLAN SD-T4) | `{"r,c": float}`; diffuse fallback only (FR-T2) |
| `opponent_hint: str` | CT-03 `hint` (last received) | **verbal phase only** — never a move input (FR-T7) |
| `arena: str` | shared game.json | hint content |
| `deadline: float | None` | C04 | template mode ignores it; provider mode (T027) bounds the call |

### 5.3 Output

| Output | Consumer | Notes |
|---|---|---|
| `Decision` (frozen dataclass, table below) | C04 turn loop (applies `action`), C03 (seals commit fields) | the CT-02 response; additive-only contract |
| `Decision.hint` | CT-03 `TurnMessage.hint` | ≤ 15 words, free NL, may lie (STRAT-009) |
| `Decision.action` + `verdict` + `prompt_text` | commit preimage via C03 (canonical JSON, SPEC §2) | plain serializable values only |

| Field | Type | Notes |
|---|---|---|
| `action` | `str` | one member of the CT-01 legal set (incl. `"STAY"`) |
| `barrier_cell` | `Cell | None` | **always `None` for Thief** (FR-T4); Police-only, requires `action == "STAY"` |
| `hint` | `str` | ≤ `hint_max_words` words (FR-T6) |
| `verdict` | `str` | `"truth" \| "lie"` — sealed into the commit chain (SPEC §3) |
| `fallback` | `bool` | `True` when forced `STAY` (legal set was `["STAY"]` only) |
| `reasoning` | `str` | `""` for template mode |
| `prompt_text` | `str` | sealed (`prompt_discussion`) for audit; `""` for template mode |
| `response_seconds` | `float` | timing metadata for the hint phase; never a decision input |

## 6. Constraints & Limitations

### 6.1 Constraints

- The policy selects only from the CT-01 legal set (M-04 binding); legality is guaranteed
  upstream and re-checked at the domain boundary (`apply_own_move` raises `IllegalMoveError`)
  — the policy does not reimplement physics.
- Signed values are fixed and consumed, never redefined: 7×7 board, move set
  `N,S,E,W,STAY`, barrier quota 14 (GAME-008), move cap and survival threshold 35 (GAME-014),
  arena "New York" and 15-word cap (STRAT-009 defaults), `diversity_reward` 10.
- Barriers: the Thief never places one (FR-T4, domain-enforced); declared barriers are public
  and exact (GAME-012) and are hard inputs to mobility/trap scoring.
- The capture-claim answer is domain-owned and always truthful (SEC-007, FR-T5); the
  survival claim at `step >= 35` is mechanical (runtime/C03) — the policy's job is only to
  keep living.
- `step` numbering is per-peer and a step is a **round** (SPEC §7.5): the policy reads only
  its own `engine.step` and never the opponent's counter.
- Movement never depends on an unvalidated LLM output (NG-003, STRAT-008); the book's single
  LLM-tactics exception (explicit documented mutual agreement + local legality enforcement)
  is **out of scope** for this stage.
- Line cap 150 nonblank/noncomment lines per code file; no new third-party dependency (pure
  stdlib + the existing repo packages).

### 6.2 Limitations (accepted)

- **Single-step greedy, no lookahead.** The threat is a point estimate, not a distribution
  over the Police's next move; a one-move-ahead squeeze that does not box the destination in
  immediately can still land the Thief. Lookahead (minimax/expectimax over the opponent
  belief, book §6.3.1) is the P2 upgrade if self-play shows trap lag.
- **The trap-risk term is one turn deep** (`trap_risk` — at most one orthogonal exit at the
  destination only, a conservative policy heuristic, not the domain's rule-47 `boxed_in`
  capture check). Two-turn traps (the Police placing the sealing barrier next turn) are
  mitigated by mobility, not caught.
- **The diffuse fallback can sit on a stale hotspot.** Under the default one-sided
  `trust_v1` likelihood (PRD-BELIEF-BOARD §6.2) an empty received field carries no negative
  evidence; `scent.hottest` inherits that staleness. The belief stage's `kernel_bayes_v1`
  form addresses it; the policy consumes whichever the board produces.
- **`visited` is role-local per sub-game**; there is no cross-sub-game or series-level
  learning (T019 territory).
- **The lie rate is a fixed seeded constant (≈ 0.4)**, not adaptive; deception quality is a
  game-theory concern of the pair, not a correctness concern of the policy (STRAT-009 allows
  either).
- **The opposite-role sub-game** (series role alternation, `role_for`) keeps the stage-2
  stand-in selection in this repository until the police stage's brain is ported (PLAN
  SD-T7); the KPI harness is role-pinned and unaffected.

## 7. Alternatives Considered

| Alternative | Trade-off | Verdict |
|---|---|---|
| **Reference distance-max** (`max(moves, key=(distance-to-peak, unvisited))`, report §5.2) | Simplest; byte-reproducible against the reference; but walks the Thief into corners (max distance ⇒ zero mobility) and ignores the trap entirely | **Rejected** as the final policy; **kept as the A/B baseline** in the KPI harness (the policy must beat it, not equal it) |
| **Scored multi-criterion heuristic** (distance + mobility + freshness − trap; selected) | Four O(1) terms, no lookahead, no training; weights are tuned project convention (PLANQ-008 records the approval); fixes the corner-walk and one-turn-trap failure modes | **Selected** — book §6.3.1's "your own heuristic algorithm" route, the reference report's identified headroom (§10 items 2–3) |
| **1-ply minimax / expectimax over the opponent belief** (book §6.3.1) | Stronger play; but needs a model of the Police's policy (meta-belief), multiplies decision cost, and complicates the determinism/audit story | Rejected for this stage; **P2**, a new task if approved |
| **Q-learning RL** (book §6.3; STRAT-007 MAY) | The book's optional route (Bellman + ε-greedy); not required, not taught in the course; stochastic without a seeded discipline; training/eval burden over a 49-cell grid | Rejected for this stage; **P2**, a new task if approved |
| **LLM-driven movement** | The book's warning box (ch. 6 §6.5): coordinate hallucination turns directly into illegal or self-defeating moves; NG-003 forbids it by default; the single exception needs explicit documented mutual agreement | **Forbidden** for this stage by default; the exception is out of scope (stated) |

## 8. Success Criteria & Test Plan

### 8.1 One own turn (sequence)

```mermaid
sequenceDiagram
    participant RT as C04 turn loop (assumed)
    participant BE as BeliefGrid (belief stage)
    participant BR as ThiefBrain (shared core + M-04)
    participant HW as HintWriter (template)
    RT->>BE: apply_half_turn (barrier?, smell_grid, hint, arena, own_cell)
    RT->>BR: note_evidence(smell_grid)      [last received field, SD-T4]
    RT->>BR: decide(state, belief, opponent_hint, arena)
    Note over BR: PHASE 1 — MOVE (pure Python, no LLM, NG-003)
    BR->>BR: legal = state.legal_moves()
    alt legal == ["STAY"] only
        BR-->>RT: Decision("STAY", fallback=True)  [forced; capture is domain-decided]
    else
        BR->>BR: threat = peak | hottest(last_field) | centre  (FR-T2)
        BR->>BR: score each legal dest: dist + mob + fresh - trap (FR-T3)
        BR->>BR: first maximum in CT-01 order; visited updated on MOVE
        BR->>HW: say(position)              [PHASE 2 — HINT, after the move]
        HW-->>BR: (hint, verdict)           [capped to 15 words; lie roll seeded]
        BR-->>RT: Decision(action, hint, verdict, ...)
    end
    RT->>RT: apply_own_move(action); C03 seals (move, verdict, prompt) into the commit
    Note over RT: a hint can never alter the already-selected action (FR-T7)
```

### 8.2 Threat selection and scoring (flow)

```mermaid
flowchart TD
    A[decide: legal set from CT-01] --> B{legal == STAY only?}
    B -- yes --> C["forced STAY, fallback=True (rule-47 capture is domain-decided)"]
    B -- no --> D{peak_probability >= min_confidence?}
    D -- yes --> E[threat = belief.most_likely]
    D -- no --> F{last received field non-empty?}
    F -- yes --> G[threat = scent.hottest(last_field)]
    F -- no --> H[threat = board centre]
    E --> S
    G --> S
    H --> S
    S[for each legal action in N,S,W,E,STAY order] --> T["score = w_dist*d/N + w_mob*mob/4 + w_fresh*fresh - w_trap*trap"]
    T --> U{strictly greater than best so far?}
    U -- yes --> V[best = this action]
    U -- no --> W[keep earlier — first maximum wins ties]
    V --> X
    W --> X[return (action, barrier=None)]
    X --> Y[PHASE 2: hint = template say(position), capped; verdict rule-computed]
```

### 8.3 Specific test cases

| ID | Test | Criterion |
|---|---|---|
| TC-T01 | construction & smoke: build the brain from a config mapping; `decide()` on a fixture state returns a `Decision` whose `action` is in `state.legal_moves()` and whose `barrier_cell` is `None` | FR-T1, FR-T4 |
| TC-T02 | legality property: 10k random (engine, belief, field) fixtures ⇒ `action` always in the legal set; `barrier_cell` always `None`; `fallback` is `True` iff the legal set was `["STAY"]` | FR-T1, FR-T4, MS-1/MS-2 |
| TC-T03 | threat selection: (a) confident peak ⇒ action maximizes distance to `most_likely()`; (b) peak below `min_confidence` + non-empty field ⇒ distance to `hottest()`; (c) below + empty ⇒ distance to board centre | FR-T2, MS-3 |
| TC-T04 | mobility term: two equidistant destinations ⇒ the one with more legal orthogonal options is selected | FR-T3 |
| TC-T05 | freshness term: equidistant + equal mobility ⇒ the unvisited destination is selected over the visited one | FR-T3, FR-T8 |
| TC-T06 | trap-risk term: a reachable destination with at most one orthogonal exit (`trap_risk`) is avoided whenever a lower-risk alternative exists (`w_trap` dominance) | FR-T3 |
| TC-T07 | forced STAY: all orthogonal moves blocked ⇒ `("STAY", None)`, `fallback=True`; `self_captured()` remains domain-decided (no policy override) | FR-T1 |
| TC-T08 | tie-break: two equally-scored actions ⇒ the earlier in CT-01 order (N, S, W, E, STAY) wins | FR-T3, NFR-2 |
| TC-T09 | template hint: output ≤ 15 words; names a landmark from the arena table (or the generic non-landmark line); `verdict` ∈ {truth, lie}; seeded lie fraction within 0.30–0.50 over 1000 generated hints (deterministic per seed) | FR-T6 |
| TC-T10 | hint isolation & NG-003: the move phase completes before the hint phase (a hint writer that raises or returns garbage leaves the action unchanged); a boom provider that raises if consulted is never consulted on the move path; a failed/deadline provider ⇒ template fallback with the action unchanged | FR-T7, CT-02 |
| TC-T11 | verdict rule: independently recomputed from position + asserted landmark region ⇒ matches the sealed `verdict` for every generated hint (rule: contains or Chebyshev-adjacent ⇒ "truth") | FR-T6 |
| TC-T12 | injection seam: explicit `thief_class` selector loads the custom class end-to-end (`isinstance`); malformed selector ⇒ `ValueError`; missing attribute ⇒ `ValueError`; non-`BrainBase` target ⇒ `TypeError`; unset selector ⇒ shipped `ThiefBrain`; the `police_class` key is ignored for Thief resolution | FR-T9 |
| TC-T13 | visited discipline: `visited` starts at `{start}`; grows only on orthogonal MOVE (not STAY); reset per sub-game; never present in `Decision` or any wire field | FR-T8, FR-T11 |
| TC-T14 | no-leak static scan: no import of opponent-truth symbols in `strategy/`; no parameter or field accepts the opponent's position | FR-T11, NFR-5 |
| TC-T15 | determinism: same seed + same wire transcript, two processes ⇒ byte-identical decision logs (action, hint, verdict, fallback at every step) | FR-T10, NFR-2, MS-5 |
| TC-T16 | performance: `decide()` ≤ 10 ms p99 over 10k iterations (7×7, CPython 3.12) | NFR-1, MS-5 |
| TC-T17 | KPI self-play (200 seeded games, role-pinned Thief sub-games, shipped config): survival vs reference `PoliceBrain` ≥ 60%; vs stage-2 stand-in ≥ 30% (labeled; re-measured vs the designed police brain when the police stage lands); median rounds-to-capture ≥ 22 | §2.3, MS-5 |
| TC-T18 | spine: the real brain on the decision path (PLAN §12 S3a/S3b/S3c; opposite-role sub-games keep the stand-in, SD-T7) ⇒ `tests/integration/test_series_loopback.py` green (full six-sub-game series settles) | MS-4 |
| TC-T19 | shared-core sync: `decision.py`, `base.py`, `hints.py`, `inject.py`, `__init__.py` identical to the police-repo counterparts modulo package import path and the role constant (ORC check; deferred until the police counterparts exist — until then single-repo internal consistency) | Goal 6, NFR-6 |

### 8.4 Milestones and deliverables (stage timeline)

| Phase | Deliverable | Exit |
|---|---|---|
| 1 (TS-02) | shared core: `decision.py`, `base.py`, `hints.py`, `inject.py`, `__init__.py`; unit suite green | TC-T01, TC-T12, TC-T14 (partial), MS-1 |
| 2 (TS-03) | `thief.py`: scored evasion, threat fallback, visited; unit suite green | TC-T02 (unit), TC-T03…T08, TC-T13, MS-2/MS-3 |
| 3 (TS-04/TS-05) | spine swap (S3a/S3b/S3c) + verbal hardening (isolation, verdict, cap, lie rate) | TC-T09…T11, TC-T18, MS-4 |
| 4 (TS-06/TS-07) | property + KPI + determinism + perf + coverage close-out; shared-core sync + docs sync | TC-T15…T19, MS-5 |

## 9. Configuration Schema

Private `config/game.toml` (local only, never signed, never sent):

```toml
[strategy]
# Optional brain override: dotted "package.module:ClassName" (FR-T9).
# Unset ⇒ the shipped ThiefBrain of this stage runs.
# thief_class = "my_team.strategy:CornerThiefBrain"

[strategy.thief]
# Project convention (NOT an official requirement) — the PLANQ-008 approval baseline.
# Score weights (FR-T3); the score is normalized per term before weighting.
w_dist = 1.0          # distance from threat, manhattan(dest, threat) / board.size
w_mob = 0.25          # mobility: legal orthogonal options at dest, / 4
w_fresh = 0.15        # freshness: dest not in visited (orthogonal MOVE only)
w_trap = 5.0          # trap: trap_risk(dest) — at most one orthogonal exit left
# Belief confidence floor (FR-T2): below it, the diffuse fallback engages.
min_confidence = 0.15
```

Shared values consumed (signed `config/game.json`, **never** redefined here):
`board_and_agents.grid_size` (normalization + geometry), `movement_and_barriers.move_set`
(legal-set order), `movement_and_barriers.max_moves` / `survival_threshold` (the survival
target), `world.map_area` (hint arena) and `world.hint_max_words` (word cap),
`network_and_league.diversity_reward` (motivates the freshness term; the weight itself is
private). Precedence: on any key conflict the shared JSON overlays the private TOML (CFG
rules); the `[strategy]` keys have no shared counterparts.

## 10. League Compatibility

The strategy is **project-native** (`docs/interop/LEAGUE_COMPATIBILITY.md`: "Strategy design
is project-native; any non-authoritative material supplies interoperability wiring only");
SPEC §1 confirms that the strategy, its prompts and its infra are private — there is **no
cross-team byte agreement on moves, hints, or barrier timing**. The kit pins bytes only
where two implementations must agree, and where this policy touches that surface:

- **TurnMessage fields the decision flows into** (CT-03, profile `reference-v3`):
  `hint` (free NL ≤ 15 words — never a numeric-position substitute, NET-003/NET-004);
  `commit` (the decision's `action` + `verdict` + `prompt_text` enter the preimage via C03
  as **plain serializable values** — `str`/`int`/`None`; `barrier_cell` serializes to
  `[r,c]` on the Police side; canonical JSON per SPEC §2: `sort_keys`, no whitespace,
  `ensure_ascii=False` — the strategy never emits a field C03 cannot serialize);
  `barrier_placed` (absent for Thief decisions — the Thief never declares, FR-T4);
  `capture_claim` / `claim_response` / `win_claim` (domain/C03-owned, SEC-007 — not policy
  fields, FR-T5).
- **The truthful capture exchange** (SPEC §3.1, rules 21–22): the rule-46/47 endings are
  visible only to the Thief and **must be said** by the Thief or the game forks (two honest
  peers, two different stories, rule-35 zero). The announcement is the runtime/C03's
  mechanical job (the `caught: true` final); the policy never gates, delays, or suppresses
  it — its only contribution is to keep the Thief alive until the announcement is made or
  not made honestly.
- **Open barrier declarations** (rules 15–16, GAME-012): the policy treats declared barriers
  as exact public truth (mobility/trap inputs, FR-T3) — a hidden barrier is disqualifying
  for the *declarer*, and the Thief's own belief board excludes them (belief FR-B4); the
  policy adds no second reading of them.
- **`step` = round, per-peer numbering** (SPEC §7.5): two peers reading "35" as rounds vs.
  half-turns desync even when every signed term matches, and no gate catches it. The policy
  reads only its own `engine.step` and never the opponent's counter; the survival claim at
  the threshold is the runtime's, not the policy's.
- **Scent-lock calibration** is the **belief** board's responsibility (kit §5: "a wrong port
  makes your belief map behave unlike the book's"); the policy consumes the locked profile
  through the belief and `hottest` boundaries only (ADR-004 consequence).
- **Adopted profile** (ADR-004 / `LEAGUE_COMPATIBILITY.md`): `wire_shape reference-v3`,
  scent `subtractive_chebyshev_v1` default (+ `multiplicative_book_v1` supported),
  `info_mode belief`. The policy must not conflict with it and does not touch it: it neither
  declares nor compares locked models (C03/C01 territory), and `info_mode belief` is exactly
  the input regime the policy is built for.

## 11. Out of Scope

- The Police policy (M-03; `police_repo`, planned trio) — including its barrier-placement
  decision; this document's shared-core sections are its mirror, not its content.
- The belief board itself (`PRD-BELIEF-BOARD`, sibling stage-3 work; assumed by the entry
  criteria for this PRD's consumption surface).
- The optional language-model provider adapter (T027, P2, `optional: true`, gated by
  PLANQ-003/PLANQ-004 `blocks: start` on that task only) — the provider-neutral
  `TextProvider` seam (FR-T6/FR-T7) is defined in the shared core; the implementation is
  deferred. The book's LLM-tactics exception is out of scope (stated, §6.1).
- Reinforcement learning and lookahead (book §6.3/§6.3.1 — STRAT-007 allows, does not
  require; P2, a new task if approved).
- Capture-claim answer implementation (domain, T004) and commit sealing (C03, T008) — the
  policy consumes both as constraints.
- The survival-claim mechanism (runtime/C03, mechanical at `step >= 35`) and series-level
  aggregation/scoring (T019) — including the `diversity_reward` settlement; the policy only
  proxies it per-decision (FR-T8).
- Opponent policy modelling (meta-belief) and adaptive deception rates — P2 candidates.

**Open items.** PLANQ-008 (`TBD_TEAM_DECISION`) gates T007's `{#heuristics}` acceptance
criterion only (`blocks: criterion` — the task proceeds; the criterion waits): the §9 values
are the approval baseline, and the KPI fixtures (TC-T17) are the seeded scenarios it
reviews. OPEN-009 (official scent saturation/merge reading) does not block this stage: the
policy consumes whichever locked profile the belief board produces (ADR-004).

## 12. References

- `docs/mechanisms/M-04-thief-strategy.md` — the binding contract (this PRD's mechanism
  contract: specified behavior, derived-design split, acceptance scenarios).
- `docs/components/C02-perception-strategy/PRD.md` / `PLAN.md` — the shared C02 component
  scope.
- `docs/contracts/CT-01-game-state.md` (legal set), `CT-02-strategy-decision.md` (this
  PRD's I/O contract, failure behavior), `CT-03-peer-wire.md` (the fields the decision
  flows into).
- `docs/decisions/ADR-004-operational-interoperability-profile.md` — adopted profile; the
  policy is profile-agnostic by construction.
- `docs/interop/LEAGUE_COMPATIBILITY.md` — strategy design is project-native.
- `docs/tasks/T007-implement-role-strategy.md` (claim unit, PLANQ-008 gate),
  `T021-close-unit-property-and-coverage-gaps.md` (property/coverage close-out),
  `T027-implement-optional-language-model-provider-adapter.md` (deferred provider).
- `docs/PRD_belief_board.md` / `PLAN_belief_board.md` / `TODO_belief_board.md` — the sibling
  shared part: the board this policy consumes (FR-B6 queries) and the `LANDMARK_CELLS` table
  it imports (SD-B3).
- `docs/PLAN_mcp_infrastructure.md` — SD-03 stand-in engine (replaced by this stage, §12
  spine) and the stub-replacement discipline this PLAN continues.
- `references/copthief-league-protocol/SPEC.md` §1 (private strategy), §2 (canonical JSON),
  §3.1 (one-sided endings, `caught: true`), §7.5 (wire surface; step is a round) — the
  compatibility surface of §10.
- Project book ch. 6 (§6.2 separate strategy module; §6.3/§6.3.1 the three movement routes;
  §6.4 belief + Manhattan; §6.5/§6.5.1 verbal layer + four provider modes) and ch. 10
  (stage order; the 3+4 fold, §1.1).
- `docs/report-game-p2p-cop-chase-strategy.md` §5 (the reference brains, the `Decision`
  shape, the injection seam) and §10 (the extension headroom this
  stage claims) — non-authoritative reference implementation; registered evidence only, per
  LEAGUE_COMPATIBILITY.
- `police_repo/docs/PRD_police_strategy.md` (planned) — the mirror of the shared-core
  sections.

## 13. Relationship to the Repository Documents

- **Upstream:** M-04 (the binding mechanism contract this PRD decomposes); the C02
  component PRD/PLAN (shared scope); CT-01/CT-02/CT-03 (legal set, decision contract,
  wire fields the decision flows into); ADR-004 + `LEAGUE_COMPATIBILITY.md` (the profile
  §10 must not conflict with, and does not touch).
- **Siblings (same stage, separate files):** the belief trio
  (`docs/PRD_belief_board.md` + `PLAN` + `TODO`) — the shared half this policy consumes
  (FR-B6 queries, the `LANDMARK_CELLS` table); the planned police trio
  (`police_repo/docs/PRD_police_strategy.md` + `PLAN` + `TODO`) — the mirror of the
  shared-core sections and the owner of the pursuit policy.
- **Execution:** `docs/TODO_thief_strategy.md` (this stage's ledger) maps to repo task
  T007 (claim unit; PLANQ-008 `blocks: criterion` on `{#heuristics}`), with T021 for the
  property/coverage close-out and T027 deferred and gated. The global `docs/TODO.md` is
  reconciled by the orchestrator after each wave; this PRD does not carry live task
  state.
- **Assumed delivered (stage entry criteria):** C01 domain + config (T003/T004), scent
  model + lock (T005), orchestrator FSM + turn loop (T010), MCP transport + turn frames
  (T009), integrity core (T008); the belief board (T006) is the sibling stage-3 work.
