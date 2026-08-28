"""Recover one completed SG2 from captured real MCP wire evidence."""

from __future__ import annotations

import json
from pathlib import Path

from common.domain.scoring import Outcome, Role, score_for
from common.transport.audit import audit_records
from common.transport.audit_wire import KitAuditWire
from common.transport.replay_evidence import SubgameReplayEvidence, capture_subgame_evidence
from common.transport.series import SeriesRow


def _read(directory: Path, name: str) -> object:
    with (directory / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def recover_sg2(
    directory: Path | str,
    *,
    terms: dict,
) -> tuple[SeriesRow, SubgameReplayEvidence]:
    """Verify both SG2 audits and all observed commitments."""
    source = Path(directory)
    wire = KitAuditWire()
    opponent_audit = wire.inbound(_read(source, "sg2_submit_audit_incoming.json"))
    own_audit = wire.inbound(_read(source, "sg2_submit_audit_reply.json"))
    turns = _read(source, "sg2_incoming_turns.json")
    if not isinstance(opponent_audit, dict) or not isinstance(own_audit, dict):
        raise ValueError("resume SG2 audits must normalize to objects")
    if not isinstance(turns, list):
        raise ValueError("resume SG2 turns must be a JSON list")
    played = {
        int(turn["step"]): str(turn["commit"])
        for turn in turns
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
            "resume SG2 audit verification failed: "
            f"opponent={opponent_result.detail!r}, own={own_result.detail!r}"
        )
    if own_audit.get("result_claim") != "survival" or opponent_audit.get("result_claim") != "survival":
        raise ValueError("resume SG2 result claims are not identical survival outcomes")
    steps = len(own_records) - 1
    if steps != 35 or len(played) != 35:
        raise ValueError(f"resume SG2 evidence is incomplete: own_steps={steps}, incoming={len(played)}")
    row = SeriesRow(
        sub_game_number=2,
        role=Role.POLICE,
        outcome=Outcome.SURVIVAL,
        steps=steps,
        score_police=score_for(Outcome.SURVIVAL, Role.POLICE),
        score_thief=score_for(Outcome.SURVIVAL, Role.THIEF),
        audit_ok=True,
    )
    evidence = capture_subgame_evidence(
        sub_game_index=2,
        terms=terms,
        own_records_raw=own_records,
        opponent_records_raw=opponent_records,
        observed_opponent_commitments=played,
        our_result_claim="survival",
        opponent_result_claim="survival",
        row=row,
    )
    return row, evidence
