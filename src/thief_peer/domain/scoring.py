"""How a sub-game ends, and what it is worth (book ch.3 table 2; App. F table 17).

Every value here is `קבוע` — permanent in the binding table, not negotiable in either direction.
They live in one place so that nothing else in the package can quietly hold a second copy.
"""

from common.domain.scoring import (
    SCORES,
    SUB_GAMES_PER_SERIES,
    TIE_SCORE,
    ZEROED,
    Outcome,
    Role,
    is_tie_row,
    role_for,
    score_for,
    settled_outcome,
)

__all__ = [
    "Outcome",
    "Role",
    "SCORES",
    "SUB_GAMES_PER_SERIES",
    "TIE_SCORE",
    "ZEROED",
    "is_tie_row",
    "role_for",
    "score_for",
    "settled_outcome",
]

__all__ = [
    "Outcome",
    "Role",
    "SCORES",
    "SUB_GAMES_PER_SERIES",
    "TIE_SCORE",
    "ZEROED",
    "is_tie_row",
    "role_for",
    "score_for",
    "settled_outcome",
]
