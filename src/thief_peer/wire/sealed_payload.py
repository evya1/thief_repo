"""How a decision becomes the ONE payload this peer seals for a turn (T054).

Split out of ``session.py`` so that module owns only the mutable sub-game lifecycle and
this one owns payload construction. Both wire adapters (`BrainDrivenEngine`,
`StandInEngine`) compose these two functions rather than each keeping a copy: a sealed
payload is evidence, and two copies of it are two places for the kit-required post-move
`position` -- or the concession cell -- to drift apart. A drift between the two engines
would surface only as an opponent's audit failure, at the worst possible moment.

Both functions are the single construction boundary the kit `position` port lands on: the
value is derived once, here, from the engine's own state *after* the action is applied and
*before* the record is committed. It is never appended to the envelope after hashing, and
``PUBLIC_TURN_KEYS`` does not project it, so it reaches neither the opponent's turn message
nor an LLM prompt.

Role delta vs. the Police peer: this repository routes the truthful capture exchange
through ``wire.capture_exchange`` (``declare_own_action`` / ``resolve_claims``), which owns
the GAME-006/009/012 declaration rules. The `position` binding and the terminal-final
derivation are identical in both repositories.
"""

from __future__ import annotations

from typing import Any

from common.domain.board import Cell
from common.domain.scoring import Role
from thief_peer.wire.capture_exchange import declare_own_action, resolve_claims
from thief_peer.wire.session import SubgameSession


def _own_cell(engine) -> list[int]:
    """This peer's own post-action cell as the kit's `[row, col]`."""
    return [int(engine.position[0]), int(engine.position[1])]


def build_result(
    session: SubgameSession,
    *,
    move: str,
    hint: str,
    verdict: str = "truth",
    fallback: bool = False,
    reasoning: str = "",
    prompt_text: str = "",
    response_seconds: float = 0.0,
    barrier_cell: Cell | None = None,
) -> dict[str, Any]:
    """Build the ONE sealed result for this turn (Decision metadata + own smell_grid +
    declarations + claim handling); ``subgame.py`` derives the public projection from it --
    never build a second outgoing dict.

    The truthful capture exchange (GAME-006/009/012) is runtime-owned protocol, not a
    strategy concern, so ``declare_own_action`` attaches this peer's own declarations for
    whichever role it holds this sub-game.
    """
    engine, trail = session.engine, session.trail
    assert engine is not None and trail is not None
    res: dict[str, Any] = {
        "move": move,
        "barrier_cell": list(barrier_cell) if barrier_cell is not None else None,
        "hint": hint,
        "verdict": verdict,
        "fallback": fallback,
        "reasoning": reasoning,
        "prompt_text": prompt_text,
        "response_seconds": response_seconds,
        "state": engine.state_string(),
        # The pinned kit's full artifact physics walker dereferences `payload["position"]`
        # and cannot walk a game without it; `state` spells the same cell but the walker
        # reads both and cross-checks them, so they must be one derivation.
        "position": _own_cell(engine),
        "smell_grid": trail.full_turn(engine.position),
    }
    declare_own_action(engine, res, barrier_cell)
    caught = resolve_claims(engine, res, session.pending_claim, session.pending_claim_position)
    session.pending_claim = None
    session.pending_claim_position = None
    session.thief_caught = session.thief_caught or caught
    return res


def build_terminal_final(session: SubgameSession) -> dict[str, Any] | None:
    """Return the sealed game-ending final step this peer owes, or None (rule 35).

    A thief that saw its own capture (rules 46/47 -- a fact only the thief can see) owes a
    concession: a STAY naming its own final cell with ``caught: true``. A police settling
    from the thief's final owes a plain sealed STAY. An answered claim or a survival claim
    already rode the last normal step, so only the invisible capture needs the extra step.
    """
    engine = session.engine
    if engine is None:
        return None
    smell_grid = session.trail.full_turn(engine.position) if session.trail is not None else {}
    is_thief = engine.role is Role.THIEF
    if is_thief and engine.self_captured() is None:
        return None
    if not is_thief and session.terminal() is None:
        return None
    session.apply_move("STAY")
    cell = _own_cell(engine)
    final: dict[str, Any] = {
        "move": "STAY",
        "hint": "",
        "state": engine.state_string(),
        "position": cell,
        "smell_grid": smell_grid,
    }
    if is_thief:
        final["claim_response"] = {"claim": cell, "caught": True}
    return final
