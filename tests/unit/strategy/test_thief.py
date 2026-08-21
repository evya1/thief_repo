"""ThiefBrain tests: threat selection, scoring, tie-break, trap avoidance.

TC-T02 (unit): legality property.
TC-T03: threat selection — three branches.
TC-T04: mobility term.
TC-T05: freshness term.
TC-T06: trap term.
"""

from __future__ import annotations

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from src.thief_peer.strategy.thief import ThiefBrain


class _UniformBelief:
    """Uniform belief: peak probability = 1/N²."""

    def __init__(self, board: Board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)


class _PeakBelief:
    """Belief with a single peak at the given cell."""

    def __init__(self, board: Board, peak: tuple[int, int]) -> None:
        self._board = board
        self._peak = peak
        self._size = board.size

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return 0.9


class TestThreatSelection:
    """TC-T03: threat selection — three branches of FR-T2."""

    def test_confident_peak(self) -> None:
        """Peak above min_confidence => threat = most_likely()."""
        brain = ThiefBrain(min_confidence=0.15)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _PeakBelief(board, (6, 6))
        action, _ = brain._decide_move(engine, belief)
        assert action in ("MOVE:N", "MOVE:W", "STAY")

    def test_diffuse_scent_fallback(self) -> None:
        """Peak below min_confidence + non-empty field => threat = hottest."""
        brain = ThiefBrain(min_confidence=0.15)
        brain.note_evidence({"0,0": 0.9, "6,6": 0.1})
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        assert action in ("MOVE:S", "MOVE:E", "STAY")

    def test_empty_field_centre_fallback(self) -> None:
        """Peak below min_confidence + empty field => threat = board centre."""
        brain = ThiefBrain(min_confidence=0.15)
        brain.note_evidence({})
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        assert action in ("MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E")

    def test_boundary_min_confidence(self) -> None:
        """min_confidence exactly at boundary => peak branch taken (>=)."""
        brain = ThiefBrain(min_confidence=0.9)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _PeakBelief(board, (6, 6))
        action, _ = brain._decide_move(engine, belief)
        assert action in ("MOVE:N", "MOVE:W", "STAY")


class TestMobilityTerm:
    """TC-T04: two equidistant destinations => the one with more legal options wins."""

    def test_mobility_preferred(self) -> None:
        brain = ThiefBrain(w_dist=1.0, w_mob=0.25, w_fresh=0.0, w_trap=5.0)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(1, 1))
        belief = _PeakBelief(board, (1, 1))
        action, _ = brain._decide_move(engine, belief)
        assert action == "MOVE:S"


class TestFreshnessTerm:
    """TC-T05: equidistant + equal mobility => unvisited preferred over visited."""

    def test_freshness_preferred(self) -> None:
        brain = ThiefBrain(w_dist=1.0, w_mob=0.0, w_fresh=0.15, w_trap=5.0)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        brain.reset((3, 3))
        brain.visited.add((2, 3))
        action, _ = brain._decide_move(engine, belief)
        assert action != "MOVE:N"


class TestTrapTerm:
    """TC-T06: a destination that would be boxed_in next turn is avoided."""

    def test_trap_avoided(self) -> None:
        brain = ThiefBrain(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=5.0)
        board = Board(size=7)
        barriers = [(0, 2), (2, 2), (1, 3)]
        engine = GameEngine(board=board, role=Role.THIEF, position=(1, 1), barriers=barriers)
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        assert action != "MOVE:E"
