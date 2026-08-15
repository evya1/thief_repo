"""Domain layer: pure per-peer game logic (no I/O, no network).

Board geometry, movement legality, barrier placement, capture/terminal
conditions, and the fixed scoring table.  Both peers import this module
and compute identical results from identical inputs.
"""

from common.domain import (
    Board,
    Cell,
    GameEngine,
    IllegalMoveError,
    Move,
    MOVES,
    ORTHOGONAL,
    Outcome,
    Role,
    SCORES,
    TIE_SCORE,
    ZEROED,
    is_tie_row,
    score_for,
    settled_outcome,
)

__all__ = [
    "Board",
    "Cell",
    "GameEngine",
    "IllegalMoveError",
    "Move",
    "MOVES",
    "Outcome",
    "ORTHOGONAL",
    "Role",
    "SCORES",
    "TIE_SCORE",
    "ZEROED",
    "is_tie_row",
    "score_for",
    "settled_outcome",
]
