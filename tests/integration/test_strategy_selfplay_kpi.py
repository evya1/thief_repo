"""KPI self-play harness fixtures: a police opponent CAPABLE OF CAPTURING.

TC-T17: survival vs a capturing police opponent >= 60%; vs a weaker
labeled baseline >= 30%. Rewritten per PR #34 review H5: the previous
"reference" opponents were bare StandInEngine subclasses that never placed
a barrier and never issued a capture claim, so the thief could not lose --
the KPI passed for any policy, including always-STAY. The double here
(``GreedyCapturingPolice``) actually pursues and claims capture; it is a
TEST-ONLY double (registered evidence, non-authoritative, SD-T7) and is
built entirely from the same public ``TurnEngine`` seam production code
uses -- it does not read hidden state through any strategy-module API, only
through a test-harness-only position hook wired directly between the two
in-process engine objects below (never through thief_peer.strategy).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from common.domain.board import manhattan
from common.domain.scoring import Role
from thief_peer.strategy.scoring import destination
from thief_peer.wire.session import SubgameSession


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


def _terminal_final(session: SubgameSession | None) -> dict | None:
    """The game-ending final an engine owes after settling, or None.

    Roles alternate across the series, so a double may play both sides: a
    thief owes the rules-46/47 concession only on an invisible capture (an
    answered claim or a survival claim already rode the last normal step);
    a police settling from the thief's final owes a plain sealed STAY.
    """
    if session is None or session.engine is None:
        return None
    eng = session.engine
    trail = session.trail
    smell_grid = trail.full_turn(eng.position) if trail is not None else {}
    if eng.role is Role.THIEF:
        if eng.self_captured() is None:
            return None
        session.apply_move("STAY")
        return {
            "move": "STAY",
            "hint": "",
            "state": eng.state_string(),
            "smell_grid": smell_grid,
            "claim_response": {"claim": [int(eng.position[0]), int(eng.position[1])], "caught": True},
        }
    if session.terminal() is None:
        return None
    session.apply_move("STAY")
    return {"move": "STAY", "hint": "", "state": eng.state_string(), "smell_grid": smell_grid}


class GreedyCapturingPolice:
    """A police opponent that actually pursues and claims capture.

    Test double only: ``thief_position_fn`` is a harness-level hook the KPI
    test wires directly between the two in-process engine objects it
    constructs -- it never touches ``thief_peer.strategy`` or any production
    module, so no hidden opponent truth leaks into the code under test.
    """

    def __init__(
        self,
        natural_role: Role = Role.POLICE,
        board_size: int = 7,
        seed: int = 0,
        terms: dict | None = None,
        thief_position_fn: Callable[[], tuple[int, int]] | None = None,
    ) -> None:
        self.natural_role = natural_role
        self.board_size = board_size
        self.seed = seed
        self.terms = terms
        self.thief_position_fn = thief_position_fn
        self._session: SubgameSession | None = None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        self._session = SubgameSession(natural_role=self.natural_role, board_size=self.board_size, seed=self.seed)
        self._session.start(sub_game, role, terms=terms or self.terms)

    def decide(self) -> dict:
        """Pursue. The claim itself comes from the shared runtime session, which
        now declares this peer's own post-action cell on every POLICE non-barrier
        turn (MEDIUM-8) -- the double contributes pursuit, not protocol."""
        assert self._session is not None and self._session.engine is not None
        engine = self._session.engine
        target = self.thief_position_fn() if self.thief_position_fn else engine.position
        legal = engine.legal_moves()
        best = min(
            legal,
            key=lambda a: manhattan(destination(engine.board, engine.position, a), target),
        )
        self._session.apply_move(best)
        return self._session.build_result(move=best, hint="closing in")

    def observe_opponent(self, message: dict) -> None:
        if self._session is not None and self._session.engine is not None:
            self._session.observe_barrier_and_claims(message)

    def terminal(self):
        return self._session.terminal() if self._session else None

    def terminal_final(self) -> dict | None:
        return _terminal_final(self._session)


class AlwaysStayThiefEngine:
    """Negative control: a thief that always STAYs (mandatory negative control)."""

    def __init__(self, natural_role: Role = Role.THIEF, board_size: int = 7, seed: int = 0) -> None:
        self.natural_role = natural_role
        self.board_size = board_size
        self.seed = seed
        self._session: SubgameSession | None = None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        self._session = SubgameSession(natural_role=self.natural_role, board_size=self.board_size, seed=self.seed)
        self._session.start(sub_game, role, terms=terms)

    def decide(self) -> dict:
        assert self._session is not None
        self._session.apply_move("STAY")
        return self._session.build_result(move="STAY", hint="not moving")

    def observe_opponent(self, message: dict) -> None:
        if self._session is not None and self._session.engine is not None:
            self._session.observe_barrier_and_claims(message)

    def terminal(self):
        return self._session.terminal() if self._session else None

    def terminal_final(self) -> dict | None:
        return _terminal_final(self._session)


@dataclass
class KPIResult:
    total_thief_subgames: int
    survived: int
    captured: int
    capture_rounds: list[int]
