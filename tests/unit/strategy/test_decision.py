"""Decision contract tests.

TC-T01: construction & smoke — build from config; decide() returns a Decision
whose action is in state.legal_moves() and whose barrier_cell is None.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from thief_peer.strategy import Decision, resolve_brain


class TestDecisionConstruction:
    """TC-T01: Decision construction and field invariants."""

    def test_default_values(self) -> None:
        d = Decision(action="MOVE:N")
        assert d.barrier_cell is None
        assert d.hint == ""
        assert d.verdict == "truth"
        assert d.fallback is False
        assert d.reasoning == ""
        assert d.prompt_text == ""
        assert d.response_seconds == 0.0

    def test_immutable(self) -> None:
        d = Decision(action="MOVE:S", hint="hello", verdict="lie", fallback=True)
        with pytest.raises(AttributeError):
            d.action = "STAY"  # type: ignore[misc]

    def test_serializable_projection(self) -> None:
        d = Decision(action="MOVE:N", barrier_cell=None, hint="here", verdict="truth")
        assert d.action == "MOVE:N"
        assert d.barrier_cell is None
        assert d.hint == "here"
        assert d.verdict == "truth"


class TestSmoke:
    """TC-T01 smoke: build the brain from config; decide() returns legal action."""

    def test_brain_constructible(self) -> None:
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.THIEF)
        assert brain is not None

    def test_decide_returns_legal_action(self) -> None:
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.THIEF)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action in engine.legal_moves()
        assert decision.barrier_cell is None

    def test_forced_stay(self) -> None:
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.THIEF)
        board = Board(size=7)
        # Box the thief in at (1,1)
        barriers = [(0, 1), (2, 1), (1, 0), (1, 2)]
        engine = GameEngine(board=board, role=Role.THIEF, position=(1, 1), barriers=barriers)
        belief = _UniformBelief(board)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert decision.fallback is True


class _UniformBelief:
    """Minimal belief stub: uniform distribution."""

    def __init__(self, board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)
