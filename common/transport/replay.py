"""Headless replay verification — the book's Replay Viewer, minus the GUI.

Reuses the single canonical integrity path (M-05). No import from the reference kit.
Verdicts are exactly ``Verified OK``, ``TAMPERED``, or ``ILLEGAL`` (FR-RP-08).
"""

from __future__ import annotations

import json
from pathlib import Path

from common.transport.audit import AuditResult, audit_records
from common.transport.canonical import commit as hash_commit
from common.transport.replay_records import from_kit_record, is_foreign_record


def _terms_beside(path: Path) -> dict:
    """Read signed terms from a config_*.json artifact in the same directory, if one is there.

    Arms the audit's physics layer offline: board bound, barrier quota, step ceiling. The
    BINDING layer (revealed vs received commits) is inherently in-play knowledge and cannot be
    reconstructed from artifacts — replay is integrity + physics; the live audit is all three.
    """
    for cfg_path in sorted(path.parent.glob("config_*.json")):
        try:
            terms = json.loads(cfg_path.read_text(encoding="utf-8")).get("terms")
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(terms, dict):
            return terms
    return {}


def _verify_foreign_half(records: list[dict]) -> AuditResult:
    """Integrity-only re-hash for foreign-shaped records (D-03, FR-RP-10).

    Skips intent enforcement and physics checks; only verifies that each record
    reproduces its stored commitment. A missing intent in a foreign record is a
    degradation note, never TAMPERED.
    """
    failed: list[int] = []
    tampered: list[int] = []
    notes: list[str] = []
    verified = 0

    for record in records:
        flat = from_kit_record(record)
        step = int(flat.get("step", -1))
        commit = flat.get("commit")
        if commit is None:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing commit")
            continue
        payload = {k: v for k, v in flat.items() if k not in ("commit", "nonce")}
        nonce = flat.get("nonce", "")
        computed = hash_commit(payload, nonce)
        if computed != commit:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: committed {commit}, rehash {computed}")
        else:
            if step >= 1:
                verified += 1

    notes.append(
        "degraded coverage: foreign-shaped records verified integrity-only; "
        "physics and intent not enforced"
    )
    return AuditResult(
        passed=len(failed) == 0,
        verified_steps=verified,
        failed_steps=failed,
        tampered_steps=tampered,
        detail="; ".join(notes[:3]) if notes else "",
    )


def _verify_half(records: list[dict], terms: dict) -> AuditResult:
    """Verify one half of a log (own or opponent).

    Own-shaped halves: full four-layer audit (binding/outcome inert offline).
    Foreign halves: integrity-only re-hash, with explicit degraded-coverage note.
    """
    if not records:
        return AuditResult(passed=True, verified_steps=0)
    if is_foreign_record(from_kit_record(records[0]).get("payload", {})):
        return _verify_foreign_half(records)
    flat_records = [from_kit_record(r) for r in records]
    return audit_records(flat_records, played={}, terms=terms)


def verify_log(path: Path) -> tuple[bool, str]:
    """Return ``(ok, human-readable report)`` for one log artifact.

    Own-shaped halves go through the full four-layer audit. Foreign halves
    verify integrity-only with a degraded-coverage note (D-03, FR-RP-10).
    Verdict split (FR-RP-08): tampered_steps → TAMPERED; failed_steps only → ILLEGAL.
    """
    doc = json.loads(path.read_text(encoding="utf-8"))
    records = doc.get("records") or []
    if not records:
        return False, f"{path.name}: no records — the game left nothing to verify"

    terms = _terms_beside(path)
    halves: list[tuple[str, list[dict]]] = [("own", records)]
    if doc.get("opponent_records"):
        halves.append(("opponent", doc["opponent_records"]))

    lines, ok, total = [], True, 0
    for label, recs in halves:
        result = _verify_half(recs, terms)
        total += len(recs)
        if result.passed:
            continue
        ok = False
        if result.tampered_steps:
            verdict = (
                f"TAMPERED — steps {result.tampered_steps} do not reproduce their commitments"
            )
        else:
            verdict = (
                f"ILLEGAL — every record re-hashes, but steps {result.failed_steps} "
                "break the signed physics"
            )
        lines.append(f"{path.name} ({label} records): {verdict}\n    {result.detail}")

    if ok:
        sides = "both sides'" if len(halves) > 1 else "one side's"
        return True, (
            f"{path.name}: Verified OK — {total} records re-hashed against their "
            f"commitments ({sides} sealed half)"
        )
    return False, "\n  ".join(lines)


def verify_dir(root: Path) -> tuple[int, int, list[str]]:
    """Recurse log_*.json under root (D-05); aggregate ok/bad counts and lines."""
    lines: list[str] = []
    ok = bad = 0
    for path in sorted(root.rglob("log_*.json")):
        good, report = verify_log(path)
        lines.append(("  " if good else "  ") + report)
        ok = ok + 1 if good else ok
        bad = bad + 1 if not good else bad
    return ok, bad, lines


def cross_check_uid(root: Path) -> str | None:
    """All four artifacts must carry one game_uid — the key that joins them.

    A replay that verifies every record of a log belonging to a *different*
    match has proved nothing at all (FR-RP-06).
    """
    uids: set[str] = set()
    for path in sorted(root.rglob("*.json")):
        try:
            uid = json.loads(path.read_text(encoding="utf-8")).get("game_uid")
        except (ValueError, UnicodeDecodeError):
            continue
        if uid is not None:
            uids.add(uid)
    if len(uids) > 1:
        return (
            f"artifacts carry {len(uids)} different game_uids: {sorted(uids)} — they do not "
            "all belong to one match, so verifying them together proves nothing"
        )
    return None
