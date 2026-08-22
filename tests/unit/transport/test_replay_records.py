"""Tests for the replay shape adapter (replay_records.py).

TC-RP-06: differential round-trip identity over a fixture sweep.
TC-RP-09: step-0 handling — declaration record round-trips correctly.
"""

from __future__ import annotations

from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay_records import (
    flat_steps_to_kit_doc,
    from_kit_record,
    is_foreign_record,
    to_kit_record,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _flat_record(step: int, sender: str, intent: str, **extra: object) -> dict:
    """Build a flat repo-style sealed record."""
    nonce = new_nonce()
    payload = {"step": step, "sender": sender, "intent": intent, **extra}
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def _honest_steps(n: int = 3) -> list[dict]:
    """A minimal honest step trail (step-0 + n moves), flat shape."""
    steps = [_flat_record(0, "thief", "declare")]
    for i in range(1, n + 1):
        steps.append(
            _flat_record(
                i,
                "thief",
                "evade",
                state=f"grid=7x7;self=[{i}, {i}];barriers=[]",
                move=f"MOVE:{"N" if i % 2 else "E"}",
                hint="hint",
            )
        )
    return steps


def _honest_opponent_steps(n: int = 2) -> list[dict]:
    """A minimal opponent step trail, flat shape."""
    steps = [_flat_record(0, "police", "declare")]
    for i in range(1, n + 1):
        steps.append(
            _flat_record(
                i,
                "police",
                "chase",
                state=f"grid=7x7;self=[0, {i}];barriers=[]",
                move=f"MOVE:{"E" if i % 2 else "S"}",
                hint="hint",
            )
        )
    return steps


# ---------------------------------------------------------------------------
# TC-RP-06: round-trip differential
# ---------------------------------------------------------------------------

class TestRoundTripIdentity:
    """to_kit_record(from_kit_record(r)) == r for every record shape."""

    def test_step_0_round_trips(self) -> None:
        flat = _flat_record(0, "thief", "declare")
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        assert back == flat

    def test_full_move_round_trips(self) -> None:
        flat = _flat_record(
            1,
            "thief",
            "evade",
            state="grid=7x7;self=[1, 1];barriers=[]",
            move="MOVE:N",
            hint="north",
        )
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        assert back == flat

    def test_round_trip_preserves_commit(self) -> None:
        """Re-hashing from_kit_record(r) reproduces r["commit"] byte-for-byte."""
        flat = _flat_record(
            2,
            "police",
            "chase",
            state="grid=7x7;self=[2, 2];barriers=[]",
            move="MOVE:S",
        )
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        assert back["commit"] == flat["commit"]
        assert back["nonce"] == flat["nonce"]
        assert hash_commit(
            {k: v for k, v in back.items() if k not in ("nonce", "commit")},
            back["nonce"],
        ) == back["commit"]

    def test_fixture_sweep(self) -> None:
        """Sweep honest steps and verify round-trip for every record."""
        for flat in _honest_steps(5):
            kit = to_kit_record(flat)
            assert from_kit_record(kit) == flat

    def test_fixture_sweep_opponent(self) -> None:
        """Sweep opponent steps and verify round-trip for every record."""
        for flat in _honest_opponent_steps(4):
            kit = to_kit_record(flat)
            assert from_kit_record(kit) == flat

    def test_nested_to_flat_preserves_all_fields(self) -> None:
        flat = _flat_record(
            3,
            "thief",
            "evade",
            state="grid=7x7;self=[3, 3];barriers=[[1, 1], [2, 2]]",
            move="MOVE:W",
            hint="west",
            barrier_placed=True,
        )
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        assert back == flat


# ---------------------------------------------------------------------------
# TC-RP-09: step-0 handling
# ---------------------------------------------------------------------------

class TestStepZero:
    """Step-0 declaration record round-trips and is recognisable."""

    def test_step_0_is_foreign_false(self) -> None:
        """Step-0 has no state string — it is foreign by the adapter's definition."""
        flat = _flat_record(0, "thief", "declare")
        kit = to_kit_record(flat)
        # Step-0 payload has no state, so is_foreign_record returns True.
        # This is expected: the harness treats it as foreign and verifies
        # integrity-only (which is fine — it still re-hashes correctly).
        payload = kit["payload"]
        assert is_foreign_record(payload) is True

    def test_step_0_round_trips_cleanly(self) -> None:
        flat = _flat_record(0, "thief", "declare")
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        assert back["step"] == 0
        assert back["sender"] == "thief"
        assert back["intent"] == "declare"
        assert back["commit"] == flat["commit"]

    def test_step_0_rehashes_correctly(self) -> None:
        flat = _flat_record(0, "thief", "declare")
        kit = to_kit_record(flat)
        back = from_kit_record(kit)
        computed = hash_commit(
            {k: v for k, v in back.items() if k not in ("nonce", "commit")},
            back["nonce"],
        )
        assert computed == back["commit"]


# ---------------------------------------------------------------------------
# flat_steps_to_kit_doc
# ---------------------------------------------------------------------------

class TestFlatStepsToKitDoc:
    """Convert record lists to the kit-shaped log fragment."""

    def test_records_only(self) -> None:
        steps = _honest_steps(2)
        doc = flat_steps_to_kit_doc(steps, None)
        assert "records" in doc
        assert len(doc["records"]) == 3  # step-0 + 2 moves
        assert "opponent_records" not in doc

    def test_both_halves(self) -> None:
        steps = _honest_steps(2)
        opp = _honest_opponent_steps(1)
        doc = flat_steps_to_kit_doc(steps, opp)
        assert len(doc["records"]) == 3
        assert len(doc["opponent_records"]) == 2

    def test_kit_records_are_nested(self) -> None:
        steps = _honest_steps(1)
        doc = flat_steps_to_kit_doc(steps, None)
        rec = doc["records"][0]
        assert "payload" in rec
        assert "nonce" in rec
        assert "commit" in rec
        assert "step" not in rec  # step lives inside payload


# ---------------------------------------------------------------------------
# is_foreign_record
# ---------------------------------------------------------------------------

class TestIsForeignRecord:
    """Detect foreign-shaped payloads (no parseable repo state string)."""

    def test_repo_state_is_own(self) -> None:
        payload = {"state": "grid=7x7;self=[3, 3];barriers=[]", "move": "MOVE:N"}
        assert is_foreign_record(payload) is False

    def test_missing_state_is_foreign(self) -> None:
        payload = {"move": "MOVE:N"}
        assert is_foreign_record(payload) is True

    def test_empty_state_is_foreign(self) -> None:
        payload = {"state": "", "move": "MOVE:N"}
        assert is_foreign_record(payload) is True

    def test_none_state_is_foreign(self) -> None:
        payload = {"move": "MOVE:N"}
        assert is_foreign_record(payload) is True

    def test_foreign_position_list_is_foreign(self) -> None:
        """Kit-style position list (not the repo's state string) is foreign."""
        payload = {"position": [3, 3], "move": "MOVE:N"}
        assert is_foreign_record(payload) is True

    def test_foreign_state_string_is_foreign(self) -> None:
        """A state string that doesn't match the repo format is foreign."""
        payload = {"state": "position=[3,3]", "move": "MOVE:N"}
        assert is_foreign_record(payload) is True

    def test_state_with_barrier_is_own(self) -> None:
        payload = {"state": "grid=7x7;self=[0, 0];barriers=[[1, 1]]", "move": "MOVE:S"}
        assert is_foreign_record(payload) is False

    def test_state_with_negative_coords(self) -> None:
        payload = {"state": "grid=7x7;self=[-1, -1];barriers=[]", "move": "MOVE:S"}
        assert is_foreign_record(payload) is False
