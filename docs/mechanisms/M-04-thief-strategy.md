---
artifact: mechanism-prd
id: M-04
component: C02
status: draft
shared: false — Thief only
owner: orchestrator
updated: 2026-08-15
---

# M-04 — Thief Strategy

## Why this mechanism has its own PRD

Evasion/escape-preservation/truthful-capture-response decision policy is genuinely role-specific and must never leak into the Police repository (that is what makes it worth separating from the shared C02 component PRD, and worth keeping fully role-specific — this file exists only in `thief_repo`).

## Governing requirements

ARCH-007 (strategy is a separate module), STRAT-007 (movement policy freedom — heuristic, custom algorithm, or RL, none required), STRAT-008 (verbal-text boundary), STRAT-009 (hint negotiability).

## Specified behavior (binding)

- Movement policy may use heuristics, a custom algorithm, or reinforcement learning; none is required (STRAT-007).
- The policy selects only from C01's legal-action set (via CT-01); it never invents an action.
- During a Capture Claim the Thief must tell the truth; a false denial of a true capture causes immediate disqualification (SEC-007, owned by C03, consumed here as a hard constraint on the policy).

## Thief-specific decision shape (derived design, not an official requirement)

Evasion prioritizes moving away from the peak of the belief distribution the Thief holds about Police (M-02's output), preserving legal-move options (avoiding cells that reduce future mobility), and avoiding cells adjacent to a known barrier when an alternative exists. This is this project's own engineering choice — PLANQ-008 records the approved heuristic priorities and seeded scenarios once the team decides them; it is not itself a canonical requirement.

## Verbal-hint boundary

Hint generation (template or optional provider, STRAT-008) is isolated from movement selection by the same module boundary ARCH-007 requires. A hint may be truthful or deceptive (STRAT-009); it never determines the selected action.

## Acceptance scenarios

- [ ] The evasion policy always selects from C01's legal-action set. {#evasion_legality}
- [ ] A Capture Claim response is always truthful, including a true denial when no capture condition holds. {#capture_response_honesty}
- [ ] Hint generation cannot influence the already-selected movement action. {#hint_isolation}

## Owning task

T007 (`ARCH-007, STRAT-007…009`), depends on T004, T006.
