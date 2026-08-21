"""Spine property tests: determinism and brain-driven integration.

NFR-1: deterministic seed => byte-identical ledger.
TC-T18: spine with real ThiefBrain on THIEF sub-games, stand-in on POLICE.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesResult, run_series
from tests.integration.test_series_loopback import (
    DeterministicEngine,
    DummyBudgets,
    _full_terms,
    _strategy_config,
)


def test_deterministic_seed() -> None:
    """NFR-1: deterministic seed => byte-identical ledger across two runs."""
    def run_once() -> tuple[SeriesResult, SeriesResult]:
        a, b = pair("Police", "Thief")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_full_terms,
            seed=42,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_full_terms,
            seed=42,
        )
        engine_a = DeterministicEngine(Role.POLICE, seed=42)
        engine_b = DeterministicEngine(Role.THIEF, seed=42)
        return run_series(a, b, config_a, config_b, engine_a, engine_b)

    result_a1, result_b1 = run_once()
    result_a2, result_b2 = run_once()

    assert len(result_a1.ledger) == len(result_a2.ledger)
    assert len(result_b1.ledger) == len(result_b2.ledger)

    for _i, (row1, row2) in enumerate(zip(result_a1.ledger, result_a2.ledger, strict=True), start=1):
        assert row1.sub_game_number == row2.sub_game_number
        assert row1.role == row2.role
        assert row1.steps == row2.steps


def test_brain_driven_spine() -> None:
    """TC-T18: spine with real ThiefBrain on THIEF sub-games, stand-in on POLICE.

    S3a/S3b/S3c wired: BrainDrivenEngine replaces stand-in on THIEF path.
    POLICE sub-games keep stand-in (SD-T7). Full six-sub-game series settles.
    """
    from src.thief_peer.wire import BrainDrivenEngine

    a, b = pair("Police", "Thief")

    config_a = PeerConfig(
        natural_role=Role.POLICE,
        budgets=DummyBudgets(),
        terms=_full_terms,
        seed=42,
    )
    config_b = PeerConfig(
        natural_role=Role.THIEF,
        budgets=DummyBudgets(),
        terms=_full_terms,
        seed=42,
    )

    engine_a = DeterministicEngine(Role.POLICE)
    engine_b = BrainDrivenEngine(Role.THIEF, config=_strategy_config, seed=42)

    result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)

    assert isinstance(result_a, SeriesResult)
    assert isinstance(result_b, SeriesResult)
    assert len(result_a.ledger) == 6
    assert len(result_b.ledger) == 6

    for row in result_a.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"
    for row in result_b.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"

    assert result_a.settled is True
    assert result_b.settled is True
