"""Performance test: decide() <= 10 ms p99 over 10k iterations.

TC-T16: p99 latency <= 10 ms on 7x7 board, CPython 3.12.
"""

from __future__ import annotations

import time

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


def test_performance_p99() -> None:
    """TC-T16: decide() <= 10 ms p99 over 10k iterations."""
    config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
    brain = resolve_brain(config, Role.THIEF)
    board = Board(size=7)
    engine = GameEngine(board=board, role=Role.THIEF, position=(3, 3))
    belief = _UniformBelief(board)
    brain.reset((3, 3))

    times = []
    for _ in range(10_000):
        start = time.monotonic()
        brain.decide(engine, belief, "", "New York")
        elapsed = (time.monotonic() - start) * 1000  # ms
        times.append(elapsed)
        legal = engine.legal_moves()
        move = legal[0] if legal else "STAY"
        engine.apply_own_move(move)

    times.sort()
    p99_index = int(len(times) * 0.99)
    p99 = times[min(p99_index, len(times) - 1)]
    median = times[len(times) // 2]
    print(f"\nPerf: p99={p99:.2f} ms, median={median:.2f} ms over 10k iterations")
    assert p99 <= 10.0, f"p99 latency {p99:.2f} ms exceeds 10 ms budget"
