"""SubgameSession — the mutable game lifecycle shared by both wire adapters.

Neither ``StandInEngine`` nor ``BrainDrivenEngine`` subclasses the other;
both compose one of these. It owns exactly what is genuinely shared: the
fresh-per-sub-game ``GameEngine``, this peer's own outgoing scent trail,
capture-claim bookkeeping, and terminal-state tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.domain.board import Board, Cell
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from thief_peer.scent.model import Trail, make_trail
from thief_peer.wire.capture_exchange import (
    absorb_declarations,
    claim_hits_own_cell,
    declare_own_action,
    resolve_claims,
)


@dataclass
class SubgameSession:
    """Shared mutable lifecycle: engine, own trail, claims, terminal state."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0
    scent_model: str | None = None

    engine: GameEngine | None = None
    trail: Trail | None = None
    opponent_terminal: Outcome | None = None
    pending_claim: tuple | None = None
    pending_claim_position: Cell | None = None
    thief_caught: bool = False

    def start(self, sub_game: int, role: Role, terms: dict | None = None) -> GameEngine:
        """Fresh GameEngine + fresh own-scent Trail for this sub-game. No leaked state."""
        t = terms or {}
        board_size = t.get("board_size", self.board_size)
        max_steps = int(t.get("max_steps", 35))
        survival_threshold = int(t.get("survival_threshold", max_steps))
        max_moves = int(t.get("max_moves", max_steps))
        barriers_max = int(t.get("barriers_max", 14))

        if max_moves != survival_threshold or max_steps != survival_threshold:
            raise ValueError(
                f"divergent max_moves/max_steps ({max_steps}) and survival_threshold "
                f"({survival_threshold}) refused (OPEN-011)"
            )

        board = Board(size=board_size)
        if role is Role.POLICE:
            cop_start = t.get("cop_start", (0, 0))
            position = tuple(cop_start) if isinstance(cop_start, (list, tuple)) else (0, 0)
        else:
            thief_start = t.get("thief_start", (3, 3))
            position = tuple(thief_start) if isinstance(thief_start, (list, tuple)) else (3, 3)

        self.engine = GameEngine(
            board=board,
            role=role,
            position=position,
            max_steps=max_steps,
            survival_threshold=survival_threshold,
            barriers_max=barriers_max,
        )
        self.trail = make_trail(
            board_size,
            model=self.scent_model,
            field_size=int(t.get("smell_grid_size", 5)),
            emit_intensity=float(t.get("emit_intensity", 0.9)),
            decay_per_step=float(t.get("decay_per_step", 0.1)),
            min_center_intensity=float(t.get("min_center_intensity", 0.5)),
        )
        self.opponent_terminal = None
        self.pending_claim = None
        self.pending_claim_position = None
        self.thief_caught = False
        return self.engine

    def apply_move(self, move: str) -> None:
        assert self.engine is not None
        self.engine.apply_own_move(move)

    def observe_barrier_and_claims(self, message: dict) -> None:
        """Absorb an opponent's declared barrier + capture-claim bookkeeping.

        Delegates to ``capture_exchange.absorb_declarations``, which owns the
        pre-move snapshot rule (GAME-009 / SEC-007) and raises before mutating.
        """
        assert self.engine is not None
        claim, judged_at, terminal = absorb_declarations(self.engine, message)
        if claim is not None:
            self.pending_claim = claim
            self.pending_claim_position = judged_at
        if terminal is not None:
            self.opponent_terminal = terminal

    def capture_landed_on_own_cell(self, message: dict) -> bool:
        """True iff this half-turn's incoming capture_claim names our own current cell."""
        assert self.engine is not None
        return claim_hits_own_cell(self.engine, message)

    def build_result(
        self,
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
        """Build the ONE sealed result for this turn (Decision metadata + own
        smell_grid + declarations + claim handling); ``subgame.py`` derives the
        public projection from it -- never build a second outgoing dict.

        The truthful capture exchange (GAME-006/009/012) is runtime-owned
        protocol, not a strategy concern, so ``declare_own_action`` attaches this
        peer's own declarations for whichever role it holds this sub-game.
        """
        assert self.engine is not None and self.trail is not None
        smell_grid = self.trail.full_turn(self.engine.position)
        res: dict[str, Any] = {
            "move": move,
            "barrier_cell": list(barrier_cell) if barrier_cell is not None else None,
            "hint": hint,
            "verdict": verdict,
            "fallback": fallback,
            "reasoning": reasoning,
            "prompt_text": prompt_text,
            "response_seconds": response_seconds,
            "state": self.engine.state_string(),
            "smell_grid": smell_grid,
        }
        declare_own_action(self.engine, res, barrier_cell)
        caught = resolve_claims(self.engine, res, self.pending_claim, self.pending_claim_position)
        self.pending_claim = None
        self.pending_claim_position = None
        self.thief_caught = self.thief_caught or caught
        return res

    def terminal(self) -> Outcome | None:
        if self.opponent_terminal is not None:
            return self.opponent_terminal
        if self.thief_caught:
            return Outcome.CAPTURE
        if self.engine is not None and self.engine.role is Role.THIEF:
            if self.engine.self_captured():
                return Outcome.CAPTURE
            if self.engine.survived():
                return Outcome.SURVIVAL
        return None
