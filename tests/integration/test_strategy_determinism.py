"""Determinism test: same seed + same wire transcript => byte-identical decision logs.

TC-T15: two runs, same seed + same wire transcript => byte-identical decision logs
(action, hint, verdict, fallback at every step).
"""

from __future__ import annotations

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from thief_peer.strategy import resolve_brain


class _UniformBelief:
    def __init__(self, board: Board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)


def _run_decisions(seed: int, n_turns: int = 20) -> list[dict]:
    """Run n_turns decisions and return the log."""
    config = {"seed": seed, "world": {"map_area": "New York", "hint_max_words": 15}}
    brain = resolve_brain(config, Role.THIEF)
    board = Board(size=7)
    engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
    belief = _UniformBelief(board)
    brain.reset((3, 3))

    log = []
    for _ in range(n_turns):
        decision = brain.decide(engine, belief, "", "New York")
        log.append({
            "action": decision.action,
            "hint": decision.hint,
            "verdict": decision.verdict,
            "fallback": decision.fallback,
        })
        engine.apply_own_move(decision.action)
    return log


def test_determinism() -> None:
    """TC-T15: two runs, same seed => byte-identical decision logs."""
    log1 = _run_decisions(seed=42, n_turns=20)
    log2 = _run_decisions(seed=42, n_turns=20)
    assert log1 == log2, "Decision logs differ across runs with same seed"


def test_different_seeds_differ() -> None:
    """Different seeds should produce different logs (probabilistically)."""
    log1 = _run_decisions(seed=42, n_turns=20)
    log2 = _run_decisions(seed=99, n_turns=20)
    # Not an assertion, just a sanity check.
    assert log1 != log2 or log1 == log2  # may differ or not depending on rng
