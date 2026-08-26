"""Validated recovery of a settled SG1 and an accepted SG2 boundary."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from common.domain.scoring import Outcome, Role, score_for
from common.transport.audit import audit_records
from common.transport.audit_wire import KitAuditWire
from common.transport.kit_identity import identity_from_greeting
from common.transport.negotiate import verify_greeting
from common.transport.replay_evidence import capture_subgame_evidence
from common.transport.series import SeriesResume, SeriesRow
from thief_peer.wire.resume_sg2 import recover_sg2


def _read(directory: Path, name: str) -> object:
    with (directory / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def load_sg2_resume(
    directory: Path | str,
    *,
    terms: dict,
    group_id: str,
    locks: dict[str, str] | None = None,
    settled_sg2_dir: Path | str | None = None,
) -> SeriesResume:
    """Validate captured real wire evidence before resuming at SG2."""
    source = Path(directory)
    sg1_in = _read(source, "sg1_negotiate_incoming.json")
    sg1_reply = _read(source, "sg1_negotiate_reply.json")
    sg2_in = _read(source, "sg2_negotiate_incoming.json")
    sg2_reply = _read(source, "sg2_negotiate_reply.json")
    if not all(isinstance(value, dict) for value in (sg1_in, sg1_reply, sg2_in, sg2_reply)):
        raise ValueError("resume greetings must be JSON objects")

    agreed1 = verify_greeting(sg1_in, terms, group_id, 1, our_locks=locks)
    agreed2 = verify_greeting(sg2_in, terms, group_id, 2, our_locks=locks)
    if agreed1.opponent_group != agreed2.opponent_group:
        raise ValueError("resume evidence changes opponent between SG1 and SG2")
    if sg1_in.get("role") != Role.POLICE.value or sg1_reply.get("role") != Role.THIEF.value:
        raise ValueError("resume SG1 roles are not aviayeli Police / ZeroOne0 Thief")
    if sg2_in.get("role") != Role.THIEF.value or sg2_reply.get("role") != Role.POLICE.value:
        raise ValueError("resume SG2 roles are not aviayeli Thief / ZeroOne0 Police")
    for reply, index in ((sg1_reply, 1), (sg2_reply, 2)):
        verify_greeting(reply, terms, agreed1.opponent_group, index, our_locks=locks)
        if reply.get("accepted") is not True or reply.get("ok") is not True:
            raise ValueError(f"resume SG{index} counter-greeting was not accepted")

    wire = KitAuditWire()
    opponent_wire = _read(source, "sg1_submit_audit_incoming.json")
    own_wire = _read(source, "sg1_submit_audit_reply.json")
    opponent_audit = wire.inbound(opponent_wire)
    own_audit = wire.inbound(own_wire)
    if not isinstance(opponent_audit, dict) or not isinstance(own_audit, dict):
        raise ValueError("resume audits must normalize to objects")
    incoming_turns = _read(source, "sg1_incoming_turns.json")
    if not isinstance(incoming_turns, list):
        raise ValueError("resume incoming turns must be a JSON list")
    played = {
        int(turn["step"]): str(turn["commit"])
        for turn in incoming_turns
        if isinstance(turn, dict) and "step" in turn and "commit" in turn
    }
    own_records = own_audit.get("records", [])
    opponent_records = opponent_audit.get("records", [])
    own_played = {
        int(record["step"]): str(record["commit"])
        for record in own_records
        if isinstance(record, dict) and int(record.get("step", 0)) >= 1
    }
    opponent_result = audit_records(
        opponent_records,
        played,
        terms,
        our_records=own_records[1:],
        our_result_claim=own_audit.get("result_claim"),
        opponent_result_claim=opponent_audit.get("result_claim"),
    )
    own_result = audit_records(own_records, own_played, terms)
    if not opponent_result.passed or not own_result.passed:
        raise ValueError(
            "resume SG1 audit verification failed: "
            f"opponent={opponent_result.detail!r}, own={own_result.detail!r}"
        )
    if own_audit.get("result_claim") != "capture" or opponent_audit.get("result_claim") != "capture":
        raise ValueError("resume SG1 result claims are not identical captures")
    steps = len(own_records) - 1
    if steps != 25 or len(played) != 25:
        raise ValueError(f"resume SG1 evidence is incomplete: own_steps={steps}, incoming={len(played)}")

    row = SeriesRow(
        sub_game_number=1,
        role=Role.THIEF,
        outcome=Outcome.CAPTURE,
        steps=steps,
        score_police=score_for(Outcome.CAPTURE, Role.POLICE),
        score_thief=score_for(Outcome.CAPTURE, Role.THIEF),
        audit_ok=True,
    )
    evidence = capture_subgame_evidence(
        sub_game_index=1,
        terms=terms,
        own_records_raw=own_records,
        opponent_records_raw=opponent_records,
        observed_opponent_commitments=played,
        our_result_claim="capture",
        opponent_result_claim="capture",
        row=row,
    )
    evidence = replace(evidence, game_id=agreed1.game_id, game_uid=agreed1.game_uid)
    rows = (row,)
    evidence_entries = (evidence,)
    next_sub_game = 2
    if settled_sg2_dir is not None:
        sg2_row, sg2_evidence = recover_sg2(settled_sg2_dir, terms=terms)
        rows += (sg2_row,)
        evidence_entries += (
            replace(sg2_evidence, game_id=agreed1.game_id, game_uid=agreed1.game_uid),
        )
        next_sub_game = 3
    return SeriesResume(
        game_id=agreed1.game_id,
        game_uid=agreed1.game_uid,
        opponent_group_id=agreed1.opponent_group,
        opponent_identity=identity_from_greeting(sg1_in),
        ledger=rows,
        replay_evidence=evidence_entries,
        next_sub_game=next_sub_game,
    )
