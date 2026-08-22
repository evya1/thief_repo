"""Phase 8: single outbound sealed/public result — commit recomputation proof.

Proves the sealed payload (used for the commit hash and the audit record)
retains Decision metadata (reasoning, prompt_text, verdict, fallback,
response_seconds, smell_grid) that the public wire message deliberately
does NOT expose, and that the commit hash is recomputable from exactly the
sealed payload the record carries -- metadata was not discarded before
sealing.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.canonical import commit as hash_commit
from common.transport.subgame import _our_move
from thief_peer.wire.session import SubgameSession


def _thief_session() -> SubgameSession:
    session = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=0)
    session.start(1, Role.THIEF, terms={"board_size": 7, "thief_start": [3, 3], "cop_start": [0, 0]})
    return session


class _FixedMoveEngine:
    """Minimal TurnEngine.decide() double returning a full Decision-shaped result."""

    def __init__(self, session: SubgameSession) -> None:
        self._session = session

    def decide(self) -> dict:
        self._session.apply_move("MOVE:N")
        return self._session.build_result(
            move="MOVE:N",
            hint="I'm near the harbor.",
            verdict="lie",
            fallback=False,
            reasoning="internal reasoning text",
            prompt_text="internal prompt text",
            response_seconds=0.002,
        )


class TestSealedPublicProjection:
    def test_commit_recomputes_from_sealed_payload(self) -> None:
        session = _thief_session()
        engine = _FixedMoveEngine(session)
        message, record = _our_move(engine, Role.THIEF, is_thief=True, lap=1, sub_game=1)

        # The commit hash is recomputable from the sealed payload + nonce.
        sealed_payload = {k: v for k, v in record.items() if k not in ("nonce", "commit")}
        recomputed = hash_commit(sealed_payload, record["nonce"])
        assert recomputed == record["commit"] == message["commit"]

    def test_sealed_payload_retains_private_metadata(self) -> None:
        session = _thief_session()
        engine = _FixedMoveEngine(session)
        _message, record = _our_move(engine, Role.THIEF, is_thief=True, lap=1, sub_game=1)

        assert record["reasoning"] == "internal reasoning text"
        assert record["prompt_text"] == "internal prompt text"
        assert record["verdict"] == "lie"
        assert record["response_seconds"] == 0.002
        assert "state" in record  # own numeric position, sealed-only
        assert "smell_grid" in record

    def test_public_message_excludes_private_fields(self) -> None:
        session = _thief_session()
        engine = _FixedMoveEngine(session)
        message, _record = _our_move(engine, Role.THIEF, is_thief=True, lap=1, sub_game=1)

        for private_field in ("reasoning", "prompt_text", "verdict", "state", "response_seconds"):
            assert private_field not in message, f"{private_field} leaked into the public message"

    def test_public_message_carries_smell_grid_hint_and_commit(self) -> None:
        session = _thief_session()
        engine = _FixedMoveEngine(session)
        message, _record = _our_move(engine, Role.THIEF, is_thief=True, lap=1, sub_game=1)

        assert message["hint"] == "I'm near the harbor."
        assert "smell_grid" in message
        assert isinstance(message["commit"], str) and len(message["commit"]) == 64
        assert message["step"] == 1
        assert message["sender"] == Role.THIEF.value
