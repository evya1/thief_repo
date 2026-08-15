"""Board geometry and move legality (book ch.3).

App. F fixes the move set permanently: one orthogonal step, or stay. **No diagonals** — an
illegal move is rejected by the opposing agent, which enforces the physics on its own side.
Barriers are placed only by the cop, only in a turn where it forgoes movement, only on its own
cell or one orthogonally adjacent, and they are impassable **to both players for the rest of the
game**.
"""

from common.domain.board import (
    MOVES,
    ORTHOGONAL,
    Board,
    Cell,
    Move,
    chebyshev,
    manhattan,
)

__all__ = [
    "Board",
    "Cell",
    "Move",
    "MOVES",
    "ORTHOGONAL",
    "chebyshev",
    "manhattan",
]
