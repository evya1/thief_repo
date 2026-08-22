"""MEDIUM-8: the POLICE half of the capture exchange is runtime-owned protocol.

Before this, ``SubgameSession.build_result`` emitted neither ``barrier_placed``
nor ``capture_claim``, so on every sub-game where this repository is assigned
the POLICE role a capture was *structurally* unreachable: the peer could never
declare one, whatever policy drove the move. These tests pin the role-agnostic
obligations (GAME-006 / GAME-009 / GAME-012 / SEC-007) at both levels — the
sealed result the session builds, and the public projection that actually
reaches the wire through ``seal_turn`` / ``PUBLIC_TURN_KEYS``.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Outcome, Role
from common.transport.turnseal import PUBLIC_TURN_KEYS, seal_turn
from thief_peer.wire.session import SubgameSession

_TERMS = {"board_size": 7, "thief_start": [3, 3], "cop_start": [2, 2]}


def _session(role: Role) -> SubgameSession:
    session = SubgameSession(natural_role=role, board_size=7, seed=0)
    session.start(1, role, terms=_TERMS)
    return session


def _public(result: dict, role: Role) -> dict:
    """The projection that actually leaves the process for this sealed result."""
    message, _record = seal_turn(dict(result), role, role is Role.THIEF, 1)
    return message


class TestPoliceDeclaresItsOwnCell:
    def test_non_barrier_move_claims_the_post_action_cell(self) -> None:
        """A MOVE names where the Police ENDS UP, not where it started."""
        session = _session(Role.POLICE)
        session.apply_move("MOVE:N")
        result = session.build_result(move="MOVE:N", hint="closing in")

        assert result["capture_claim"] == [1, 2]
        assert result["capture_claim"] == list(session.engine.position)
        assert "barrier_placed" not in result

    def test_legal_stay_still_claims_the_current_cell(self) -> None:
        """STAY is a legal action, not an abstention: the claim must still go out."""
        session = _session(Role.POLICE)
        session.apply_move("STAY")
        result = session.build_result(move="STAY", hint="holding")

        assert result["capture_claim"] == [2, 2]
        assert "barrier_placed" not in result

    @pytest.mark.parametrize("move", ["MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E", "STAY"])
    def test_every_legal_action_declares_a_claim(self, move: str) -> None:
        session = _session(Role.POLICE)
        session.apply_move(move)
        result = session.build_result(move=move, hint="")
        assert result["capture_claim"] == list(session.engine.position)


class TestBarrierAndClaimAreMutuallyExclusive:
    def test_barrier_turn_declares_placement_and_no_claim(self) -> None:
        """A barrier forfeits the move (GAME-006), so it carries no capture claim."""
        session = _session(Role.POLICE)
        target = (2, 3)
        session.engine.place_own_barrier(target)
        session.apply_move("STAY")
        result = session.build_result(move="STAY", hint="walling", barrier_cell=target)

        assert result["barrier_placed"] == [2, 3]
        assert "capture_claim" not in result

    def test_thief_turns_declare_neither(self) -> None:
        """Only the cop places barriers and only the cop claims captures."""
        session = _session(Role.THIEF)
        session.apply_move("MOVE:N")
        result = session.build_result(move="MOVE:N", hint="running")

        assert "capture_claim" not in result
        assert "barrier_placed" not in result


class TestSealedPublicProjection:
    """What actually reaches the wire — PUBLIC_TURN_KEYS, not the sealed record."""

    def test_claim_survives_the_public_projection(self) -> None:
        session = _session(Role.POLICE)
        session.apply_move("MOVE:E")
        message = _public(session.build_result(move="MOVE:E", hint="closing in"), Role.POLICE)

        assert message["capture_claim"] == [2, 3]
        assert "barrier_placed" not in message
        assert "capture_claim" in PUBLIC_TURN_KEYS

    def test_barrier_survives_and_no_claim_rides_with_it(self) -> None:
        session = _session(Role.POLICE)
        session.engine.place_own_barrier((3, 2))
        session.apply_move("STAY")
        result = session.build_result(move="STAY", hint="walling", barrier_cell=(3, 2))
        message = _public(result, Role.POLICE)

        assert message["barrier_placed"] == [3, 2]
        assert "capture_claim" not in message

    def test_projection_never_leaks_the_private_barrier_cell_field(self) -> None:
        """``barrier_cell`` is the private Decision field; ``barrier_placed`` is the
        public declaration. Only the latter is in PUBLIC_TURN_KEYS."""
        session = _session(Role.POLICE)
        session.engine.place_own_barrier((3, 2))
        session.apply_move("STAY")
        message = _public(
            session.build_result(move="STAY", hint="", barrier_cell=(3, 2)), Role.POLICE,
        )
        assert "barrier_cell" not in message
        assert set(message) <= PUBLIC_TURN_KEYS | {"commit"}


class TestClaimIsAnsweredAgainstTheArrivalSnapshot:
    def test_thief_answers_a_true_claim_honestly_after_moving_away(self) -> None:
        """SEC-007: "move away, then deny" stays impossible — the pre-move snapshot
        repaired at the current head is not regressed by the new declaration path."""
        session = _session(Role.THIEF)
        session.observe_barrier_and_claims({"capture_claim": [3, 3]})
        session.apply_move("MOVE:N")
        result = session.build_result(move="MOVE:N", hint="fleeing")

        assert result["claim_response"] == {"claim": [3, 3], "caught": True}
        assert result["win_claim"] == {"type": "capture"}
        assert session.thief_caught is True

    def test_thief_denies_a_claim_that_never_named_its_cell(self) -> None:
        session = _session(Role.THIEF)
        session.observe_barrier_and_claims({"capture_claim": [0, 0]})
        session.apply_move("STAY")
        result = session.build_result(move="STAY", hint="still here")

        assert result["claim_response"] == {"claim": [0, 0], "caught": False}
        assert "win_claim" not in result
        assert session.thief_caught is False


class TestTwoSessionExchange:
    """The declaration and the answer, wired between two sessions.

    The peer under test is a natural THIEF alternated to POLICE (the role split
    where MEDIUM-8 made a capture unreachable); ``tests/integration/
    test_playable_lifecycle.py`` runs the same exchange through the real
    sub-game loop, ledgers and audits.
    """

    def test_declared_claim_lands_and_both_sides_settle_capture(self) -> None:
        police = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=1)
        police.start(2, Role.POLICE, terms=dict(_TERMS, cop_start=[4, 3]))
        police.apply_move("MOVE:N")
        police_turn = police.build_result(move="MOVE:N", hint="closing in")
        assert police_turn["capture_claim"] == [3, 3]

        thief = SubgameSession(natural_role=Role.POLICE, board_size=7, seed=2)
        thief.start(2, Role.THIEF, terms=_TERMS)
        thief.observe_barrier_and_claims(police_turn)
        thief.apply_move("STAY")
        answer = thief.build_result(move="STAY", hint="caught")

        assert answer["claim_response"] == {"claim": [3, 3], "caught": True}
        police.observe_barrier_and_claims(answer)
        assert police.terminal() is Outcome.CAPTURE
        assert thief.terminal() is Outcome.CAPTURE
