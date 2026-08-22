"""BrainBase phase-order and visited-discipline tests.

TC-T10 (partial): phase order — move phase completes before hint phase.
"""

from __future__ import annotations

import random

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from thief_peer.strategy.base import BrainBase
from thief_peer.strategy.hints import HintWriter


class _TestBrain(BrainBase):
    """Minimal brain for testing base discipline."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def _decide_move(self, state, belief):
        return "MOVE:N", None


class _UniformBelief:
    def __init__(self, board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)


class TestPhaseOrder:
    """TC-T10 (partial): move phase completes before hint phase."""

    def test_move_before_hint(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)

        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert decision.hint != ""
        assert decision.verdict in ("truth", "lie")

    def test_fallback_decide(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        barriers = [(2, 3), (4, 3), (3, 2), (3, 4)]
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3), barriers=barriers)
        belief = _UniformBelief(board)

        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert decision.fallback is True


class TestVisitedDiscipline:
    """TC-T13: visited discipline — starts at {start}, grows only on MOVE."""

    def test_visited_starts_at_start(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)

        brain.reset((3, 3))
        assert brain.visited == {(3, 3)}

        brain.decide(engine, belief, "", "New York")
        # MOVE:N from (3,3) -> (2,3)
        assert (2, 3) in brain.visited

    def test_stay_does_not_add_to_visited(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        barriers = [(2, 3), (4, 3), (3, 2), (3, 4)]
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3), barriers=barriers)
        belief = _UniformBelief(board)

        brain.reset((3, 3))
        initial_visited = frozenset(brain.visited)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert brain.visited == initial_visited

    def test_reset_clears_visited(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)

        brain.reset((3, 3))
        brain.decide(engine, belief, "", "New York")
        assert len(brain.visited) > 1

        brain.reset((0, 0))
        assert brain.visited == {(0, 0)}


class TestHintFromDestination:
    """Phase 5: the hint is generated from the CHOSEN action's destination, never the
    pre-move position -- and never affects the already-selected move.
    """

    def test_hint_reflects_destination_not_pre_move_position(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        brain.reset((3, 3))

        # _TestBrain always picks MOVE:N -> destination (2,3), never the pre-move (3,3).
        seen_positions: list = []
        original_say = hw.say

        def spy_say(position, **kwargs):
            seen_positions.append(position)
            return original_say(position, **kwargs)

        hw.say = spy_say  # type: ignore[method-assign]
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert seen_positions == [(2, 3)]

    def test_max_words_respected_on_every_path(self) -> None:
        """max_words=3 is respected regardless of which template/provider path fires."""
        for seed in range(20):
            rng = random.Random(seed)
            hw = HintWriter(Role.THIEF, rng, "New York", 3)
            brain = _TestBrain(rng=rng, arena="New York", max_words=3, hint_writer=hw)
            board = Board(size=7)
            engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
            belief = _UniformBelief(board)
            decision = brain.decide(engine, belief, "", "New York")
            assert len(decision.hint.split()) <= 3

    def test_provider_failure_does_not_change_selected_move(self) -> None:
        """A hint provider that raises must never alter the already-selected action."""

        class BoomProvider:
            def generate(self, role, position, arena, max_words, deadline):
                raise RuntimeError("boom")

        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15, provider=BoomProvider())
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
        belief = _UniformBelief(board)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert decision.hint != ""


class TestNoteEvidence:
    """SD-T4: note_evidence stores the last received field."""

    def test_note_evidence_stores_field(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        brain.note_evidence({"0,0": 0.9, "1,1": 0.5})
        assert brain.last_field == {"0,0": 0.9, "1,1": 0.5}

    def test_note_evidence_replaces(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(Role.THIEF, rng, "New York", 15)
        brain = _TestBrain(rng=rng, arena="New York", max_words=15, hint_writer=hw)
        brain.note_evidence({"0,0": 0.9})
        brain.note_evidence({"2,2": 0.8})
        assert brain.last_field == {"2,2": 0.8}
        assert "0,0" not in brain.last_field
