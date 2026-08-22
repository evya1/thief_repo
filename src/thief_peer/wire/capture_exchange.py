"""The public half-turn declarations and the claim bookkeeping around them.

Split out of ``session.py`` (line cap), but it is genuinely one
responsibility: what this peer must truthfully *declare* about the action it
just applied, and what it must absorb from the opponent's declaration.

It is deliberately role-agnostic. Roles alternate across a series, so this
repository plays POLICE on half of its sub-games, and the capture exchange is
a *runtime protocol obligation* of whoever holds that role — not a strategy
decision. Keeping it here (rather than in a brain) is what makes a capture
structurally reachable on both sides without either repository importing the
other's policy.
"""

from __future__ import annotations

from typing import Any

from common.domain.board import Cell
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role


def _as_cell(value: Any) -> tuple[int, int]:
    """Normalize a wire coordinate (list or tuple) into a plain cell tuple."""
    return (int(value[0]), int(value[1]))


def declare_own_action(
    engine: GameEngine, result: dict[str, Any], barrier_cell: Cell | None,
) -> None:
    """Attach this peer's public declarations for the action just applied.

    ``barrier_placed`` and ``capture_claim`` are mutually exclusive. A barrier
    turn forfeits the move (GAME-006) and declares the exact placement, because
    the cop must be truthful about every barrier (GAME-012) — so it never also
    invents a move capture claim.

    Every other POLICE action turn — a legal STAY included — attaches
    ``capture_claim`` naming this peer's own POST-action cell. The Police cannot
    *know* it captured (GAME-009 / SEC-007): it states where it stands, and the
    Thief's obligatory honest answer resolves it. Omitting the claim is not a
    weak policy but a structural impossibility — no capture could ever be
    declared on the turns this repository holds the POLICE role.
    """
    if barrier_cell is not None:
        result["barrier_placed"] = list(barrier_cell)
        return
    if engine.role is Role.POLICE:
        result["capture_claim"] = list(engine.position)


def resolve_claims(
    engine: GameEngine,
    result: dict[str, Any],
    pending_claim: tuple[int, int] | None,
    judged_at: Cell | None,
) -> bool:
    """Answer any pending claim, then attach this peer's own win claim.

    Returns True iff the answer conceded a capture, which ends the sub-game
    immediately: no survival/self-capture claim may ride the same turn. The
    answer is judged at ``judged_at`` — the position captured when the claim
    ARRIVED — so a peer that has already moved cannot deny a true claim.
    """
    if pending_claim is not None:
        answer = engine.answer_capture_claim(pending_claim, at=judged_at)
        result["claim_response"] = answer
        if answer and answer.get("caught") is True:
            result["win_claim"] = {"type": "capture"}
            return True
    if engine.role is Role.THIEF:
        if engine.self_captured():
            result["win_claim"] = {"type": "capture"}
        elif engine.survived():
            result["win_claim"] = {"type": "survival"}
    return False


def _opponent_terminal(message: dict) -> Outcome | None:
    """The terminal the opponent's own message concedes or claims, if any."""
    terminal: Outcome | None = None
    response = message.get("claim_response")
    if response and response.get("caught") is True:
        terminal = Outcome.CAPTURE
    win_claim = message.get("win_claim")
    if win_claim:
        wtype = win_claim.get("type")
        if wtype == "survival":
            terminal = Outcome.SURVIVAL
        elif wtype == "capture":
            terminal = Outcome.CAPTURE
    return terminal


def absorb_declarations(
    engine: GameEngine, message: dict,
) -> tuple[tuple[int, int] | None, Cell | None, Outcome | None]:
    """Absorb the opponent's declared barrier and claims for one received turn.

    Returns ``(pending_claim, judged_at, opponent_terminal)``. A capture claim is
    judged against the position that exists RIGHT NOW, at the moment it arrives —
    before this peer's own next move can change it (GAME-009 / SEC-007: "move
    away, then deny" must not be possible). That snapshot rides with the claim
    until it is answered.

    The barrier is absorbed FIRST and may raise (off-board, over the signed
    quota) before anything else is derived, so a refused turn mutates nothing.
    """
    if "barrier_placed" in message:
        engine.observe_barrier(message["barrier_placed"])
    claim: tuple[int, int] | None = None
    judged_at: Cell | None = None
    if engine.role is Role.THIEF and "capture_claim" in message:
        claim = _as_cell(message["capture_claim"])
        judged_at = engine.position
    terminal = _opponent_terminal(message) if engine.role is Role.POLICE else None
    return claim, judged_at, terminal


def claim_hits_own_cell(engine: GameEngine, message: dict) -> bool:
    """True iff this half-turn's incoming capture_claim names our own current cell."""
    claim = message.get("capture_claim")
    return claim is not None and _as_cell(claim) == tuple(engine.position)
