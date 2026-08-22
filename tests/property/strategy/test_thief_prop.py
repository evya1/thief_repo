"""Property tests for ThiefBrain: 10k random seeded fixtures.

TC-T02 full: action always in legal set; barrier_cell always None;
fallback is True iff legal set was ["STAY"].
"""

from __future__ import annotations

import random
from unittest.mock import patch

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from thief_peer.strategy import resolve_brain
from thief_peer.strategy import thief as thief_module
from thief_peer.strategy.scoring import select_thief_action


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


def test_candidates_are_produced_by_the_real_legal_move_api() -> None:
    """Guards the trap-risk repair's root cause: scoring must never be fed a
    hand-rolled or synthetic candidate list. Every ``legal_moves`` argument
    ``select_thief_action`` receives, across 2k random reachable states, must
    equal exactly what ``GameEngine.legal_moves()`` (which delegates to
    ``Board.legal_moves``, the real legal-move API) returns for that state --
    never a fixture that invents an impossible state, such as one where the
    Thief's own origin is a barrier.
    """
    config = {"seed": 7, "world": {"map_area": "New York", "hint_max_words": 15}}
    brain = resolve_brain(config, Role.THIEF)
    rng = random.Random(11)
    board = Board(size=7)

    seen_calls = []
    scored_states = 0

    def spy(**kwargs):
        seen_calls.append(kwargs["legal_moves"])
        return select_thief_action(**kwargs)

    with patch.object(thief_module, "select_thief_action", side_effect=spy):
        for _i in range(2_000):
            pos = (rng.randint(0, 6), rng.randint(0, 6))
            barriers = []
            for _ in range(rng.randint(0, 4)):
                b = (rng.randint(0, 6), rng.randint(0, 6))
                if b != pos:  # a barrier can never land on an occupied cell (rule 46)
                    barriers.append(b)
            barriers = list(dict.fromkeys(barriers))
            assert pos not in barriers  # the origin is never a barrier (reachability invariant)

            engine = GameEngine(board=board, role=Role.THIEF, position=pos, barriers=barriers)
            legal = engine.legal_moves()
            belief = _UniformBelief(board) if rng.random() < 0.5 else _PeakBelief(
                board, (rng.randint(0, 6), rng.randint(0, 6))
            )
            brain.reset(pos)
            brain.decide(engine, belief, "", "New York")

            if legal != ["STAY"]:
                # legal == ["STAY"] short-circuits before scoring (FR-T1); otherwise
                # the exact list scoring saw must be the real legal-move API's output.
                scored_states += 1
                assert seen_calls[-1] == legal

    assert len(seen_calls) == scored_states
    assert scored_states > 0
