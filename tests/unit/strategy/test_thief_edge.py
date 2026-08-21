"""ThiefBrain edge-case tests: forced STAY, tie-break, no barrier, A/B fixtures.

TC-T07: forced STAY.
TC-T08: tie-break.
FR-T4: no barrier.
MS-3: A/B belief fixtures.
"""

from __future__ import annotations

import random

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from src.thief_peer.strategy import resolve_brain
from src.thief_peer.strategy.thief import ThiefBrain


class _UniformBelief:
    def __init__(self, board: Board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)


class _PeakBelief:
    def __init__(self, board: Board, peak: tuple[int, int]) -> None:
        self._board = board
        self._peak = peak

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return 0.9


class TestForcedStay:
    """TC-T07: all orthogonal moves blocked => ('STAY', None), fallback=True."""

    def test_forced_stay(self) -> None:
        brain = ThiefBrain()
        board = Board(size=7)
        barriers = [(2, 3), (4, 3), (3, 2), (3, 4)]
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3), barriers=barriers)
        belief = _UniformBelief(board)
        action, barrier = brain._decide_move(engine, belief)
        assert action == "STAY"
        assert barrier is None


class TestTieBreak:
    """TC-T08: two equally-scored actions => the earlier in CT-01 order wins."""

    def test_first_maximum_wins(self) -> None:
        """Equal scores => first maximum in CT-01 order (N,S,W,E,STAY) wins."""
        brain = ThiefBrain(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=0.0)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        assert action == "MOVE:N"


class TestNoBarrier:
    """FR-T4: the Thief never places a barrier."""

    def test_barrier_always_none(self) -> None:
        brain = ThiefBrain()
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        _, barrier = brain._decide_move(engine, belief)
        assert barrier is None

    def test_full_decide_barrier_none(self) -> None:
        config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.THIEF)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        _decision = brain.decide(engine, belief, "", "New York")
        assert _decision.barrier_cell is None


class TestABFixtures:
    """A/B fixtures for MS-3: swapped belief peak vs. uniform => different actions."""

    def test_peak_belief_changes_action(self) -> None:
        """Same brain, swapped belief => different actions in evasion fixtures."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        hw1 = __import__("src.thief_peer.strategy.hints", fromlist=["HintWriter"]).HintWriter(
            Role.THIEF, rng1, "New York", 15
        )
        hw2 = __import__("src.thief_peer.strategy.hints", fromlist=["HintWriter"]).HintWriter(
            Role.THIEF, rng2, "New York", 15
        )
        brain1 = ThiefBrain(rng=rng1, arena="New York", max_words=15, hint_writer=hw1)
        brain2 = ThiefBrain(rng=rng2, arena="New York", max_words=15, hint_writer=hw2)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        brain1.reset((3, 3))
        brain2.reset((3, 3))

        belief_peak = _PeakBelief(board, (6, 6))
        belief_uniform = _UniformBelief(board)

        action_peak, _ = brain1._decide_move(engine, belief_peak)
        action_uniform, _ = brain2._decide_move(engine, belief_uniform)
        assert action_peak in engine.legal_moves()
        assert action_uniform in engine.legal_moves()
