"""BrainDrivenEngine — the S3 glue swap: real ThiefBrain on THIEF sub-games.

S3a: resolve_brain(config, role) per sub-game + brain.decide(...) +
engine.apply_own_move(action).
S3b: the outgoing frame's hint comes from Decision.hint (template writer).
S3c: brain.note_evidence(smell_grid) on each received turn, before the
decision (SD-T4).

POLICE sub-games keep the stand-in selection on the existing path (SD-T7)
until the police stage's brain is ported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from common.domain.scoring import Role
from thief_peer.wire import StandInEngine


@dataclass
class BrainDrivenEngine(StandInEngine):
    """TurnEngine seam: real ThiefBrain on THIEF sub-games, stand-in on POLICE."""

    config: dict | None = None
    _brain: Any = None
    _belief: Any = None
    _last_field: dict[str, float] = field(default_factory=dict)
    _last_opponent_hint: str = ""
    _arena: str = "New York"

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        """Create a fresh GameEngine and, on THIEF sub-games, a fresh brain + belief."""
        super().start_subgame(sub_game, role, terms)
        self._brain = None
        self._belief = None
        self._last_field = {}
        self._last_opponent_hint = ""
        cfg = self.config or {}
        world = cfg.get("world")
        self._arena = str(world.get("map_area", "New York")) if isinstance(world, dict) else "New York"
        if role is Role.THIEF:
            from thief_peer.belief import build_belief
            from thief_peer.strategy import resolve_brain

            self._brain = resolve_brain(cfg, role)
            self._brain.reset(self._engine.position)
            self._belief = build_belief(self._engine.board, cfg, probe=None)

    def decide(self) -> dict:
        """Return a move dict. THIEF sub-games are brain-driven; POLICE keep the stand-in."""
        if self._engine is None:
            raise RuntimeError("start_subgame must be called before decide")

        if self._brain is not None:
            self._brain.note_evidence(self._last_field)
            decision = self._brain.decide(
                self._engine, self._belief, self._last_opponent_hint, self._arena,
            )
            self._engine.apply_own_move(decision.action)
            res: dict[str, Any] = {
                "move": decision.action,
                "hint": decision.hint,
                "state": self._engine.state_string(),
            }
            if self._pending_claim is not None:
                ans = self._engine.answer_capture_claim(self._pending_claim)
                res["claim_response"] = ans
                self._pending_claim = None
                if ans and ans.get("caught") is True:
                    self._thief_caught = True
                    res["win_claim"] = {"type": "capture"}
                    return res
            if self._engine.self_captured():
                res["win_claim"] = {"type": "capture"}
            elif self._engine.survived():
                res["win_claim"] = {"type": "survival"}
            return res

        return super().decide()

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message; feed scent + hint into the belief."""
        if "smell_grid" in message:
            self._last_field = dict(message["smell_grid"])
            if self._belief is not None:
                self._belief.observe_smell(self._last_field)
        if "hint" in message:
            self._last_opponent_hint = str(message["hint"])
            if self._belief is not None:
                self._belief.apply_hint(self._last_opponent_hint, self._arena)
        super().observe_opponent(message)
