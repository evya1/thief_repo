"""ThiefBrain — scored multi-criterion evasion policy.

The M-04 evasion policy: ranked over the CT-01 legal list (derived design —
PLANQ-008 records the approved priorities). Weights are project convention
(§9), not an official requirement. The scoring itself is pure
(``strategy/scoring.py``); this class only resolves the threat cell and
wires the pure ranking to this turn's local state.
"""

from __future__ import annotations

from common.domain.board import Cell
from common.domain.scoring import Role

from .base import BrainBase
from .scoring import ThiefWeights, select_thief_action


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
        self.weights = ThiefWeights(w_dist=w_dist, w_mob=w_mob, w_fresh=w_fresh, w_trap=w_trap)
        self.min_confidence = min_confidence
        self.role = Role.THIEF

    @property
    def w_dist(self) -> float:
        return self.weights.w_dist

    @property
    def w_mob(self) -> float:
        return self.weights.w_mob

    @property
    def w_fresh(self) -> float:
        return self.weights.w_fresh

    @property
    def w_trap(self) -> float:
        return self.weights.w_trap

    def _threat(self, state, belief) -> tuple[Cell, bool]:
        """FR-T2, fixed order: belief.most_likely() when
        belief.peak_probability() >= min_confidence; else
        scent.hottest(self.last_field); else the board centre.

        Returns (threat_cell, confident) — ``confident`` is True only for the
        belief-peak branch, and drives the H2 hard safety exclusion.
        """
        from thief_peer.scent.model import hottest

        if belief.peak_probability() >= self.min_confidence:
            return belief.most_likely(), True
        hot = hottest(self.last_field)
        if hot is not None:
            return hot, False
        size = state.board.size
        return (size // 2, size // 2), False

    def _decide_move(self, state, belief) -> tuple[str, None]:
        """Resolve the threat, then delegate to the pure ranking (FR-T3/FR-T4).

        Returns (action, None): the Thief NEVER places a barrier (FR-T4).
        """
        threat, confident = self._threat(state, belief)
        action = select_thief_action(
            board=state.board,
            position=state.position,
            barriers=state.barriers,
            legal_moves=state.legal_moves(),
            threat=threat,
            visited=frozenset(self.visited),
            weights=self.weights,
            confident_threat_cell=threat if confident else None,
        )
        return action, None
