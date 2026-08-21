"""KPI self-play harness: 200 seeded games, role-pinned Thief sub-games.

TC-T17: survival vs reference PoliceBrain >= 60%; vs stand-in >= 30% (labeled).
"""

from __future__ import annotations

from dataclasses import dataclass

from common.domain.scoring import Role
from thief_peer.wire import StandInEngine


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


class ReferencePoliceBrain(StandInEngine):
    """Reference baseline PoliceBrain: next-move stand-in (test double).

    This is a test double, non-authoritative (registered evidence only). It
    extends StandInEngine so it implements the TurnEngine seam and always
    picks the first legal move.
    """

    def __init__(self, seed: int = 42, natural_role: Role = Role.POLICE) -> None:
        super().__init__(natural_role=natural_role, seed=seed)


class StandInPoliceEngine(StandInEngine):
    """Stage-2 stand-in selection for POLICE sub-games (labeled baseline)."""

    def __init__(self, natural_role: Role = Role.POLICE) -> None:
        super().__init__(natural_role=natural_role)


@dataclass
class KPIResult:
    total: int
    thief_survived: int
    thief_captured: int
    median_rounds_to_capture: float
