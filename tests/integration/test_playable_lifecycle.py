from __future__ import annotations

import threading

import pytest

from common.domain.scoring import Outcome, Role, role_for
from common.transport.loopback import pair
from common.transport.series import PeerConfig, run_series
from common.transport.subgame import play_subgame
from thief_peer.wire import StandInEngine


class DummyBudgets:
    turn_timeout = 5.0
    connect_timeout = 5.0
    poll_interval = 0.005


_full_terms = {
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


def test_playable_lifecycle_real() -> None:
    ch_a, ch_b = pair()

    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _full_terms, seed=1)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _full_terms, seed=2)

    eng_a = StandInEngine(Role.POLICE, board_size=7, seed=1)
    eng_b = StandInEngine(Role.THIEF, board_size=7, seed=2)

    res_a, res_b = run_series(ch_a, ch_b, cfg_a, cfg_b, eng_a, eng_b)

    assert res_a.settled is True
    assert res_b.settled is True
    assert len(res_a.ledger) == 6
    assert len(res_b.ledger) == 6

    for i in range(6):
        row_a = res_a.ledger[i]
        row_b = res_b.ledger[i]
        assert row_a.sub_game_number == i + 1
        assert row_b.sub_game_number == i + 1
        assert row_a.role is role_for(Role.POLICE, i + 1)
        assert row_b.role is role_for(Role.THIEF, i + 1)
        assert row_a.outcome == row_b.outcome
        assert row_a.steps == row_b.steps
        assert row_a.score_police == row_b.score_police
        assert row_a.score_thief == row_b.score_thief
        assert row_a.audit_ok is True
        assert row_b.audit_ok is True
        assert row_a.steps > 0


def _play_pair(channels, engines, configs, sub_game: int):
    """Run one sub-game on both peers concurrently; return their two ledger rows."""
    rows: dict[str, object] = {}
    errors: list[Exception] = []

    def run(key: str, index: int) -> None:
        try:
            rows[key] = play_subgame(channels[index], engines[index], configs[index], sub_game)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run, args=("a", 0)), threading.Thread(target=run, args=("b", 1))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    if errors:
        raise RuntimeError(f"Errors in play_subgame: {errors}")
    return rows["a"], rows["b"]


class EarlyCapturePoliceEngine(StandInEngine):
    """Engine that issues a capture claim on step 2 at thief position."""

    def decide(self) -> dict:
        res = super().decide()
        engine = self._session.engine if self._session else None
        if engine and engine.role is Role.POLICE and engine.step == 2:
            res["capture_claim"] = [3, 3]
        return res


class FixedThiefEngine(StandInEngine):
    """Thief that stays at (3, 3)."""

    def decide(self) -> dict:
        if self._session is None or self._session.engine is None:
            raise RuntimeError("engine not started")
        self._session.apply_move("STAY")
        return self._session.build_result(move="STAY", hint="I am staying")


def test_early_capture_deterministic() -> None:
    """Exercise a legitimate early-capture path at step 3."""
    ch_a, ch_b = pair("Police", "Thief")
    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _full_terms, seed=1)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _full_terms, seed=2)

    eng_a = EarlyCapturePoliceEngine(Role.POLICE, board_size=7, seed=1)
    eng_b = FixedThiefEngine(Role.THIEF, board_size=7, seed=2)

    row_a, row_b = _play_pair((ch_a, ch_b), (eng_a, eng_b), (cfg_a, cfg_b), 1)

    assert row_a.outcome == Outcome.CAPTURE
    assert row_b.outcome == Outcome.CAPTURE
    assert row_a.steps == 3
    assert row_b.steps == 3
    assert row_a.score_police == 20
    assert row_a.score_thief == 5
    assert row_a.audit_ok is True
    assert row_b.audit_ok is True


def test_survival_threshold_boundaries() -> None:
    """Exercise 34/35/36 survival boundaries and divergence refusal."""
    eng = StandInEngine(Role.THIEF, board_size=7)

    # 35 threshold
    eng.start_subgame(1, Role.THIEF, terms={"max_steps": 35, "survival_threshold": 35})
    assert eng._session.engine.step == 0
    eng._session.engine.step = 34
    assert eng._session.engine.survived() is False
    eng._session.engine.step = 35
    assert eng._session.engine.survived() is True

    # 36 threshold
    eng.start_subgame(1, Role.THIEF, terms={"max_steps": 36, "survival_threshold": 36})
    eng._session.engine.step = 35
    assert eng._session.engine.survived() is False
    eng._session.engine.step = 36
    assert eng._session.engine.survived() is True

    # Divergent configuration must refuse
    with pytest.raises(ValueError, match="termination contract"):
        eng.start_subgame(1, Role.THIEF, terms={"max_steps": 34, "survival_threshold": 35})


_capture_terms = dict(_full_terms, thief_start=[3, 3], cop_start=[4, 3])


def test_alternating_role_capture_declared_by_this_peer() -> None:
    """MEDIUM-8: a capture is structurally reachable when THIS repository holds
    the POLICE role in an even (alternated) sub-game.

    The peer under test is a plain ``StandInEngine`` whose natural role is THIEF;
    ``role_for`` alternates it to POLICE in sub-game 2. Nothing here injects a
    claim: the terms place the cop one step north of a thief holding its cell, so
    the peer's own baseline selection walks onto it and ``build_result`` declares
    the capture itself. The opponent answers honestly, both ledgers settle CAPTURE
    at the same step, and both audits corroborate it. The MOVE SELECTOR is still
    the documented SD-T7 stand-in — what changed is that the runtime protocol can
    express a capture at all.
    """
    ch_a, ch_b = pair("Thief-as-police", "Police-as-thief")
    cfg_a = PeerConfig(Role.THIEF, DummyBudgets(), _capture_terms, seed=1)
    cfg_b = PeerConfig(Role.POLICE, DummyBudgets(), _capture_terms, seed=2)
    assert role_for(Role.THIEF, 2) is Role.POLICE
    eng_a = StandInEngine(Role.THIEF, board_size=7, seed=1)
    eng_b = FixedThiefEngine(Role.POLICE, board_size=7, seed=2)

    row_a, row_b = _play_pair((ch_a, ch_b), (eng_a, eng_b), (cfg_a, cfg_b), 2)

    assert row_a.role is Role.POLICE
    assert row_b.role is Role.THIEF
    assert row_a.outcome is Outcome.CAPTURE
    assert row_b.outcome is Outcome.CAPTURE
    assert row_a.steps == row_b.steps
    assert row_a.score_police == row_b.score_police == 20
    assert row_a.score_thief == row_b.score_thief == 5
    assert row_a.audit_ok is True
    assert row_b.audit_ok is True
