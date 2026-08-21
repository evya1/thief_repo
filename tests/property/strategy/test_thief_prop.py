"""Property tests for ThiefBrain: 10k random seeded fixtures.

TC-T02 full: action always in legal set; barrier_cell always None;
fallback is True iff legal set was ["STAY"].
"""

from __future__ import annotations

import random

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from src.thief_peer.strategy import resolve_brain


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

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return 0.9


def test_property_legality() -> None:
    """TC-T02 full: 10k random (engine, belief, field) fixtures."""
    config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
    brain = resolve_brain(config, Role.THIEF)
    rng = random.Random(99)
    board = Board(size=7)

    legal_violations = 0
    barrier_violations = 0
    fallback_violations = 0

    for _i in range(10_000):
        # Random position
        pos = (rng.randint(0, 6), rng.randint(0, 6))
        # Random barriers (0-4)
        num_barriers = rng.randint(0, 4)
        barriers = []
        for _ in range(num_barriers):
            b = (rng.randint(0, 6), rng.randint(0, 6))
            if b != pos:
                barriers.append(b)
        barriers = list(dict.fromkeys(barriers))  # deduplicate

        engine = GameEngine(board=board, role=Role.THIEF, position=pos, barriers=barriers)
        legal = engine.legal_moves()

        # Random belief
        if rng.random() < 0.5:
            belief = _UniformBelief(board)
        else:
            belief = _PeakBelief(board, (rng.randint(0, 6), rng.randint(0, 6)))

        # Random field
        field = {}
        if rng.random() < 0.5:
            field = {f"{rng.randint(0,6)},{rng.randint(0,6)}": rng.random() for _ in range(3)}
        brain.note_evidence(field)

        decision = brain.decide(engine, belief, "", "New York")

        # Check legality
        if decision.action not in legal:
            legal_violations += 1
        # Check barrier
        if decision.barrier_cell is not None:
            barrier_violations += 1
        # Check fallback
        if legal == ["STAY"]:
            if not decision.fallback:
                fallback_violations += 1
        else:
            if decision.fallback:
                fallback_violations += 1

        # Reset for next iteration (fresh visited set)
        brain.reset(pos)

    assert legal_violations == 0, f"Legal violations: {legal_violations}"
    assert barrier_violations == 0, f"Barrier violations: {barrier_violations}"
    assert fallback_violations == 0, f"Fallback violations: {fallback_violations}"
