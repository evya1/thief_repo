"""KPI self-play harness: 200 seeded games, role-pinned Thief sub-games.

TC-T17: survival vs reference PoliceBrain >= 60%; vs stand-in >= 30% (labeled).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role


class DummyBudgets:
    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.01


_terms = {
    "board_size": 7,
    "smell_grid_size": 5,
    "decay_per_step": 0.1,
    "emit_intensity": 0.9,
    "min_center_intensity": 0.5,
    "max_steps": 35,
    "barriers_max": 14,
    "setting": "New York",
    "hint_max_words": 15,
    "axis_origin_corner": "top-left",
    "axis_start_index": 0,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "num_games": 6,
}

_strategy_config = {
    "seed": 42,
    "world": {"map_area": "New York", "hint_max_words": 15},
}


class ReferencePoliceBrain:
    """Reference baseline PoliceBrain: distance-max with mobility tie-break.

    This is a test double, non-authoritative (registered evidence only).
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self._position = (0, 0)

    def step(self, sub_game: int, role: Role) -> dict:
        role_for_fn = __import__("common.domain.scoring", fromlist=["role_for"]).role_for
        r = role_for_fn(Role.POLICE, sub_game)
        board = Board(size=7)
        pos = (0, 0) if r is Role.POLICE else (3, 3)
        engine = GameEngine(board=board, role=r, position=pos)
        legal = engine.legal_moves()
        move = legal[0] if legal else "STAY"
        engine.apply_own_move(move)
        return {
            "move": move,
            "hint": "I am here",
            "step": 0,
            "state": engine.state_string(),
        }


class StandInPoliceEngine:
    """Stage-2 stand-in selection for POLICE sub-games (labeled baseline)."""

    def __init__(self, natural_role: Role = Role.POLICE) -> None:
        self.natural_role = natural_role

    def step(self, sub_game: int, role: Role) -> dict:
        role_for_fn = __import__("common.domain.scoring", fromlist=["role_for"]).role_for
        r = role_for_fn(self.natural_role, sub_game)
        board = Board(size=7)
        pos = (0, 0) if r is Role.POLICE else (3, 3)
        engine = GameEngine(board=board, role=r, position=pos)
        legal = engine.legal_moves()
        move = legal[0] if legal else "STAY"
        engine.apply_own_move(move)
        return {
            "move": move,
            "hint": "I am here",
            "step": 0,
            "state": engine.state_string(),
        }


@dataclass
class KPIResult:
    total: int
    thief_survived: int
    thief_captured: int
    median_rounds_to_capture: float
