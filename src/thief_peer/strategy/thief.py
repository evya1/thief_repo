"""ThiefBrain — scored multi-criterion evasion policy.

The M-04 evasion policy: ranked over the CT-01 legal list (derived design —
PLANQ-008 records the approved priorities). Weights are project convention
(§9), not an official requirement.
"""

from __future__ import annotations

from common.domain.board import Board, Cell, manhattan
from common.domain.scoring import Role

from .base import BrainBase


class ThiefBrain(BrainBase):
    """The M-04 evasion policy: scored multi-criterion ranking over the CT-01
    legal list (derived design — PLANQ-008 records the approved priorities).
    """

    def __init__(
        self,
        *,
        w_dist: float = 1.0,
        w_mob: float = 0.25,
        w_fresh: float = 0.15,
        w_trap: float = 5.0,
        min_confidence: float = 0.15,
        **base,
    ) -> None:
        super().__init__(**base)
        self.w_dist = w_dist
        self.w_mob = w_mob
        self.w_fresh = w_fresh
        self.w_trap = w_trap
        self.min_confidence = min_confidence
        self.role = Role.THIEF

    def _threat(self, state, belief) -> Cell:
        """FR-T2, fixed order: belief.most_likely() when
        belief.peak_probability() >= min_confidence; else
        scent.hottest(self.last_field); else the board centre.
        """
        from thief_peer.scent.model import hottest

        if belief.peak_probability() >= self.min_confidence:
            return belief.most_likely()
        hot = hottest(self.last_field)
        if hot is not None:
            return hot
        # Board centre: (size // 2, size // 2).
        size = state.board.size
        return (size // 2, size // 2)

    def _decide_move(
        self, state, belief
    ) -> tuple[str, None]:
        """Score each legal action in CT-01 order (N, S, W, E, STAY):

        dest     = state.board.step(state.position, action)     # STAY -> position
        d        = manhattan(dest, threat)                      # MAXIMIZE
        mobility = len(state.board.legal_moves(dest, barriers)) - 1
        fresh    = 1 if (action != "STAY" and dest not in self.visited) else 0
        trap     = 1 if state.board.boxed_in(dest, barriers) else 0
        score    = w_dist * d / size + w_mob * mobility / 4
                   + w_fresh * fresh - w_trap * trap

        Winner: FIRST maximum (strict > while scanning) — deterministic tie-break.
        Returns (action, None): the Thief NEVER places a barrier (FR-T4).
        """
        threat = self._threat(state, belief)
        board: Board = state.board
        barriers = state.barriers
        size = board.size
        position = state.position

        legal = state.legal_moves()
        best_action = legal[0]
        best_score = -float("inf")

        for action in legal:
            dest = board.step(position, action) if action != "STAY" else position
            d = manhattan(dest, threat)
            mobility = len(board.legal_moves(dest, barriers)) - 1
            fresh = 1 if (action != "STAY" and dest not in self.visited) else 0
            trap = 1 if board.boxed_in(dest, barriers) else 0
            score = (
                self.w_dist * d / size
                + self.w_mob * mobility / 4
                + self.w_fresh * fresh
                - self.w_trap * trap
            )
            if score > best_score:
                best_score = score
                best_action = action

        return best_action, None  # FR-T4: barrier_cell is always None
