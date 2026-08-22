"""Tests for the headless replay harness (replay.py).

TC-RP-02: one-byte payload mutation → TAMPERED, named step, both hashes.
TC-RP-03 ×4: physics-only failures → ILLEGAL, never TAMPERED.
TC-RP-04: two-sided opponent_records counted.
TC-RP-05: mixed-uid directory rejected.
TC-RP-08: foreign-log degradation, no false tamper.
TC-RP-10: golden determinism — same bytes → same report.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay_records import flat_steps_to_kit_doc, to_kit_record
from common.transport.replay import (
    cross_check_uid,
    verify_dir,
    verify_log,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TERMS = {
    "board_size": 7,
    "max_steps": 35,
    "barriers_max": 14,
    "setting": "New York",
    "hint_max_words": 15,
    "axis_origin_corner": "top-left",
    "axis_start_index": 0,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
}

_GAME_UID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_GAME_ID = "A-vs-B"


def _seal(payload: dict) -> dict:
    nonce = new_nonce()
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def _honest_own_steps(n: int = 3) -> list[dict]:
    """Build n honest move records (plus step-0 declaration)."""
    steps = [_seal({"step": 0, "sender": "thief", "intent": "declare"})]
    for i in range(1, n + 1):
        steps.append(
            _seal(
                {
                    "step": i,
                    "sender": "thief",
                    "intent": "evade",
                    "state": f"grid=7x7;self=[{i}, {i}];barriers=[]",
                    "move": "MOVE:N" if i % 2 else "MOVE:E",
                    "hint": "hint",
                }
            )
        )
    return steps


def _honest_opp_steps(n: int = 2) -> list[dict]:
    steps = [_seal({"step": 0, "sender": "police", "intent": "declare"})]
    for i in range(1, n + 1):
        steps.append(
            _seal(
                {
                    "step": i,
                    "sender": "police",
                    "intent": "chase",
                    "state": f"grid=7x7;self=[0, {i}];barriers=[]",
                    "move": "MOVE:E" if i % 2 else "MOVE:S",
                    "hint": "hint",
                }
            )
        )
    return steps


def _kit_log_doc(
    game_id: str,
    game_uid: str,
    own_steps: list[dict],
    opp_steps: list[dict] | None = None,
    outcome: str = "survival",
    steps: int = 3,
) -> dict:
    """Build a minimal kit-shaped log document."""
    rec_doc = flat_steps_to_kit_doc(own_steps, opp_steps)
    return {
        "schema_version": "1.1",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": {
            "declaration": f"declaration_{game_id}.json",
            "config": f"config_{game_id}_g01.json",
            "log": f"log_{game_id}_g01.json",
            "result": f"result_{game_id}.json",
        },
        "interop": {
            "label": "INTERNAL/INTEROP — NOT OFFICIAL",
            "boundary": "KitInteropAdapter",
            "authority": "book App. F table 20 (target shape); official templates pending",
        },
        "summary": {
            "sub_game_number": 1,
            "outcome": outcome,
            "steps": steps,
            "audit_ok": True,
        },
        **rec_doc,
        "mutual_agreement": {
            "our_result_claim": outcome,
            "opponent_result_claim": outcome,
            "audits_passed": True,
        },
    }


def _write_bundle(tmp: Path, log_doc: dict, own_steps: list[dict], opp_steps: list[dict] | None = None) -> Path:
    """Write a minimal replay bundle (log + config) into tmp and return tmp."""
    log_path = tmp / f"log_{_GAME_ID}_g01.json"
    log_path.write_text(json.dumps(log_doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    cfg_path = tmp / f"config_{_GAME_ID}_g01.json"
    cfg_path.write_text(
        json.dumps({"schema_version": "1.1", "game_id": _GAME_ID, "game_uid": _GAME_UID, "terms": _TERMS},
                   sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return log_path


# ---------------------------------------------------------------------------
# TC-RP-02: one-byte mutation → TAMPERED
# ---------------------------------------------------------------------------

class TestOneByteMutation:
    """TC-RP-02: a one-byte payload mutation is detected as TAMPERED."""

    def test_one_byte_mutation_tampered(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        # Mutate one byte in the second record's payload
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        doc["records"][2]["payload"]["move"] = "MOVE:W"  # was MOVE:E
        # Re-seal the tampered record
        payload = doc["records"][2]["payload"]
        nonce = doc["records"][2]["nonce"]
        doc["records"][2]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is False
        assert "TAMPERED" in report
        assert "2" in report  # named step

    def test_one_byte_state_mutation_tampered(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # Flip one byte in state
        doc["records"][2]["payload"]["state"] = doc["records"][2]["payload"]["state"].replace("[1, 1]", "[1, 2]")
        payload = doc["records"][2]["payload"]
        nonce = doc["records"][2]["nonce"]
        doc["records"][2]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is False
        assert "TAMPERED" in report


# ---------------------------------------------------------------------------
# TC-RP-03 ×4: physics-only → ILLEGAL, never TAMPERED
# ---------------------------------------------------------------------------

class TestPhysicsOnlyIllegal:
    """TC-RP-03: physics failures yield ILLEGAL, never TAMPERED (4 variants)."""

    def _make_log_with_physics_bug(self, tmp_path: Path, state_modifier: str) -> Path:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # Apply state modifier to step 1
        original_state = doc["records"][1]["payload"]["state"]
        doc["records"][1]["payload"]["state"] = original_state.replace(state_modifier[0], state_modifier[1])
        payload = doc["records"][1]["payload"]
        nonce = doc["records"][1]["nonce"]
        doc["records"][1]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        return log_path

    def test_off_board_position_is_illegal(self, tmp_path: Path) -> None:
        log_path = self._make_log_with_physics_bug(tmp_path, ("[1, 1]", "[9, 9]"))
        ok, report = verify_log(log_path)
        assert ok is False
        assert "ILLEGAL" in report
        assert "TAMPERED" not in report

    def test_jump_step_is_illegal(self, tmp_path: Path) -> None:
        """A jump > 1 orthogonal step is a physics failure."""
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # Make step 1 jump from [1,1] to [3,3]
        doc["records"][1]["payload"]["state"] = "grid=7x7;self=[3, 3];barriers=[]"
        payload = doc["records"][1]["payload"]
        nonce = doc["records"][1]["nonce"]
        doc["records"][1]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is False
        assert "ILLEGAL" in report
        assert "TAMPERED" not in report

    def test_barrier_quota_exceeded_is_illegal(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # Add many barriers to exceed quota (14)
        barriers = [[i, i] for i in range(15)]
        doc["records"][1]["payload"]["state"] = f"grid=7x7;self=[1, 1];barriers={barriers}"
        payload = doc["records"][1]["payload"]
        nonce = doc["records"][1]["nonce"]
        doc["records"][1]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is False
        assert "ILLEGAL" in report
        assert "TAMPERED" not in report

    def test_step_ceiling_exceeded_is_illegal(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # Set step to exceed ceiling (max_steps + 1 = 36)
        doc["records"][1]["step"] = 36
        payload = {k: v for k, v in doc["records"][1].items() if k not in ("nonce", "commit")}
        nonce = doc["records"][1]["nonce"]
        doc["records"][1]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is False
        assert "ILLEGAL" in report
        assert "TAMPERED" not in report


# ---------------------------------------------------------------------------
# TC-RP-04: two-sided opponent_records counted
# ---------------------------------------------------------------------------

class TestTwoSidedCounting:
    """TC-RP-04: both own and opponent records are verified and counted."""

    def test_both_halves_verified(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        opp_steps = _honest_opp_steps(2)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps, opp_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps, opp_steps)
        ok, report = verify_log(log_path)
        assert ok is True
        assert "Verified OK" in report
        # Total records = 4 own + 3 opponent = 7
        assert "7 records" in report

    def test_both_halves_named_in_report(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(2)
        opp_steps = _honest_opp_steps(2)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps, opp_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps, opp_steps)
        ok, report = verify_log(log_path)
        assert ok is True
        assert "both sides'" in report


# ---------------------------------------------------------------------------
# TC-RP-05: mixed-uid directory rejected
# ---------------------------------------------------------------------------

class TestMixedUidRejected:
    """TC-RP-05: a directory with mixed game_uids is rejected."""

    def test_cross_check_uid_clean(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(2)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        _write_bundle(tmp_path, log_doc, own_steps)
        assert cross_check_uid(tmp_path) is None

    def test_cross_check_uid_mixed(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(2)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        _write_bundle(tmp_path, log_doc, own_steps)
        # Add a second log with a different UID
        other_uid = "11111111-2222-3333-4444-555566667777"
        other_doc = _kit_log_doc(_GAME_ID, other_uid, own_steps)
        other_path = tmp_path / f"log_{_GAME_ID}_g02.json"
        other_path.write_text(json.dumps(other_doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        result = cross_check_uid(tmp_path)
        assert result is not None
        assert other_uid in result
        assert _GAME_UID in result


# ---------------------------------------------------------------------------
# TC-RP-08: foreign-log degradation, no false tamper
# ---------------------------------------------------------------------------

class TestForeignLogDegradation:
    """TC-RP-08: foreign-shaped records verify integrity-only, no false tamper."""

    def _foreign_record(self, step: int) -> dict:
        """Build a kit-style foreign record (position list, no state string)."""
        nonce = new_nonce()
        payload = {"step": step, "sender": "thief", "intent": "evade", "position": [step, step], "move": "MOVE:N"}
        return {"payload": payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}

    def test_foreign_records_no_false_tamper(self, tmp_path: Path) -> None:
        """Foreign records with valid commits pass integrity check with degraded note."""
        foreign_steps = [self._foreign_record(0), self._foreign_record(1), self._foreign_record(2)]
        log_doc = {
            "schema_version": "1.1",
            "game_id": _GAME_ID,
            "game_uid": _GAME_UID,
            "records": foreign_steps,
            "summary": {"sub_game_number": 1, "outcome": "survival", "steps": 2, "audit_ok": True},
        }
        log_path = tmp_path / f"log_{_GAME_ID}_g01.json"
        log_path.write_text(json.dumps(log_doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        # Write a config so terms is available (even though foreign path ignores it)
        cfg_path = tmp_path / f"config_{_GAME_ID}_g01.json"
        cfg_path.write_text(json.dumps({"terms": _TERMS}, sort_keys=True), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is True
        assert "Verified OK" in report
        assert "degraded coverage" in report
        assert "TAMPERED" not in report

    def test_foreign_record_missing_intent_not_tampered(self, tmp_path: Path) -> None:
        """A foreign record without intent is not flagged as TAMPERED."""
        nonce = new_nonce()
        payload = {"step": 1, "sender": "thief", "position": [1, 1], "move": "MOVE:N"}
        foreign = {"payload": payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}
        log_doc = {
            "schema_version": "1.1",
            "game_id": _GAME_ID,
            "game_uid": _GAME_UID,
            "records": [foreign],
            "summary": {"sub_game_number": 1, "outcome": "survival", "steps": 1, "audit_ok": True},
        }
        log_path = tmp_path / f"log_{_GAME_ID}_g01.json"
        log_path.write_text(json.dumps(log_doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        cfg_path = tmp_path / f"config_{_GAME_ID}_g01.json"
        cfg_path.write_text(json.dumps({"terms": _TERMS}, sort_keys=True), encoding="utf-8")
        ok, report = verify_log(log_path)
        assert ok is True
        assert "TAMPERED" not in report


# ---------------------------------------------------------------------------
# TC-RP-10: golden determinism
# ---------------------------------------------------------------------------

class TestGoldenDeterminism:
    """TC-RP-10: identical artifact bytes always produce identical reports."""

    def test_deterministic_honest_report(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        _, report1 = verify_log(log_path)
        _, report2 = verify_log(log_path)
        assert report1 == report2

    def test_deterministic_tampered_report(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(3)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        log_path = _write_bundle(tmp_path, log_doc, own_steps)
        # Tamper once
        text = log_path.read_text(encoding="utf-8")
        doc = json.loads(text)
        doc["records"][2]["payload"]["move"] = "MOVE:W"
        payload = doc["records"][2]["payload"]
        nonce = doc["records"][2]["nonce"]
        doc["records"][2]["commit"] = hash_commit(payload, nonce)
        log_path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        _, report1 = verify_log(log_path)
        _, report2 = verify_log(log_path)
        assert report1 == report2
        assert "TAMPERED" in report1

    def test_verify_dir_deterministic(self, tmp_path: Path) -> None:
        own_steps = _honest_own_steps(2)
        log_doc = _kit_log_doc(_GAME_ID, _GAME_UID, own_steps)
        d1 = tmp_path / "run1"
        d1.mkdir()
        _write_bundle(d1, log_doc, own_steps)
        d2 = tmp_path / "run2"
        d2.mkdir()
        _write_bundle(d2, log_doc, own_steps)
        ok1, bad1, lines1 = verify_dir(d1)
        ok2, bad2, lines2 = verify_dir(d2)
        assert ok1 == ok2
        assert bad1 == bad2
        assert lines1 == lines2
