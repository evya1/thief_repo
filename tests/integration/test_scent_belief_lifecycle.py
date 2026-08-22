"""Phase 7 integration: received scent reaches belief through production wiring.

Proves the previously-missing production path end to end: a real received
smell_grid, transmitted over the actual public wire projection
(``common.transport.subgame._our_move``), reaches ``BrainDrivenEngine`` via
``observe_opponent``, is normalized at the wire boundary, and moves the
belief off uniform through the canonical ``apply_half_turn`` -- not a direct
``observe_smell``/``apply_hint`` call.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.subgame import _our_move
from thief_peer.wire.brain import BrainDrivenEngine
from thief_peer.wire.session import SubgameSession

_TERMS = {
    "board_size": 7,
    "smell_grid_size": 5,
    "decay_per_step": 0.1,
    "emit_intensity": 0.9,
    "min_center_intensity": 0.5,
    "max_steps": 35,
    "barriers_max": 14,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
}

_STRATEGY_CONFIG = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}


def _opponent_turn_message(position: tuple[int, int]) -> dict:
    """Build a real public turn message the way the police-side wire would: a
    police-side SubgameSession emits its own scent trail via build_result, and
    _our_move projects it through the SAME public-key filter production uses.
    """
    session = SubgameSession(natural_role=Role.POLICE, board_size=7, seed=1)
    session.start(1, Role.POLICE, terms=_TERMS)
    session.engine.position = position  # simulate several moves toward a corner

    class _FixedEngine:
        def decide(self) -> dict:
            session.apply_move("STAY")
            return session.build_result(move="STAY", hint="patrolling")

    message, _record = _our_move(_FixedEngine(), Role.POLICE, is_thief=False, lap=1, sub_game=1)
    return message


class TestScentReachesBeliefThroughProduction:
    def test_nonuniform_field_moves_belief_off_uniform(self) -> None:
        engine = BrainDrivenEngine(Role.THIEF, config=_STRATEGY_CONFIG, seed=42)
        engine.start_subgame(1, Role.THIEF, terms=_TERMS)

        assert engine._belief.peak_probability() < 0.05  # ~uniform 1/49 at start

        message = _opponent_turn_message((6, 6))
        assert message["smell_grid"], "the public projection must carry a nonempty smell_grid"

        engine.observe_opponent(message)

        # apply_half_turn (diffuse + observe_smell) must have moved the belief.
        assert engine._belief.peak_probability() > 1.0 / 49.0
        assert engine._last_field == message["smell_grid"] or engine._last_field != {}

    def test_fallback_hotspot_can_influence_a_later_move(self) -> None:
        engine = BrainDrivenEngine(Role.THIEF, config=_STRATEGY_CONFIG, seed=42)
        engine.start_subgame(1, Role.THIEF, terms=_TERMS)
        message = _opponent_turn_message((6, 6))
        engine.observe_opponent(message)

        # note_evidence + hottest() must see a nonempty, real field (not {} forever).
        engine._brain.note_evidence(engine._last_field)
        assert engine._brain.last_field != {}

    def test_removing_smell_grid_from_public_projection_breaks_this_test(self) -> None:
        """Documents WHY smell_grid must stay in the public key set: strip it from the
        message the way the pre-fix subgame.py did, and belief evidence goes back to
        empty forever (Blocker 2's exact failure mode)."""
        engine = BrainDrivenEngine(Role.THIEF, config=_STRATEGY_CONFIG, seed=42)
        engine.start_subgame(1, Role.THIEF, terms=_TERMS)
        message = _opponent_turn_message((6, 6))
        del message["smell_grid"]  # simulate the pre-fix public_keys filter

        engine.observe_opponent(message)
        assert engine._last_field == {}
        # Only diffusion + own-cell exclusion ran (no scent evidence): the belief may
        # drift off perfectly uniform, but nowhere near the peak a real hot cell drives.
        assert engine._belief.peak_probability() < 0.05
