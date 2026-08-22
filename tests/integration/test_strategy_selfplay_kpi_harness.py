"""KPI harness continuation: run_kpi_series and test functions.

TC-T17: survival vs reference PoliceBrain >= 60%; vs stand-in >= 30% (labeled).
"""

from __future__ import annotations

from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, run_series
from tests.integration.test_strategy_selfplay_kpi import (
    DummyBudgets,
    KPIResult,
    ReferencePoliceBrain,
    StandInPoliceEngine,
    _strategy_config,
    _terms,
)


def run_kpi_series(n_games: int = 20, seed: int = 42) -> KPIResult:
    """Run n_games series of 6 sub-games each against a reference opponent.

    The default is sized for CI: each series runs the full threaded loopback
    (six sub-games, up to 35 steps each), which costs ~2s per game, so 200
    games would take minutes. Survival vs the stand-in baselines is near-100%
    in either case, well above the 60%/30% thresholds, so a smaller N keeps
    the assertion meaningful without stalling the suite.
    """
    from thief_peer.wire import BrainDrivenEngine

    total_survived = 0
    total_captured = 0
    capture_rounds: list[int] = []

    for game_seed in range(n_games):
        a, b = pair("Police", "Thief")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_terms,
            seed=seed + game_seed,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_terms,
            seed=seed + game_seed,
        )

        engine_a = ReferencePoliceBrain(seed=seed + game_seed)
        engine_b = BrainDrivenEngine(Role.THIEF, config=_strategy_config, seed=seed + game_seed)

        result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)

        thief_survived = any(
            row.outcome is Outcome.SURVIVAL and row.role is Role.THIEF
            for row in result_b.ledger
        )
        if thief_survived:
            total_survived += 1
        else:
            total_captured += 1
            for row in result_b.ledger:
                if row.outcome is Outcome.CAPTURE and row.role is Role.THIEF:
                    capture_rounds.append(row.steps)
                    break

    total = n_games
    median_rounds = 0.0
    if capture_rounds:
        sorted_rounds = sorted(capture_rounds)
        n = len(sorted_rounds)
        median_rounds = sorted_rounds[n // 2] if n % 2 == 1 else (sorted_rounds[n // 2 - 1] + sorted_rounds[n // 2]) / 2

    return KPIResult(
        total=total,
        thief_survived=total_survived,
        thief_captured=total_captured,
        median_rounds_to_capture=median_rounds,
    )


def test_kpi_vs_reference_police() -> None:
    """TC-T17: survival vs reference PoliceBrain >= 60%."""
    result = run_kpi_series(n_games=20, seed=42)
    survival_rate = result.thief_survived / result.total
    print(f"\nKPI vs reference PoliceBrain: {result.thief_survived}/{result.total} = {survival_rate:.1%}")
    print(f"Median rounds to capture: {result.median_rounds_to_capture}")
    assert survival_rate >= 0.60, f"Survival rate {survival_rate:.1%} < 60%"


def test_kpi_vs_standin() -> None:
    """TC-T17: survival vs stand-in >= 30% (labeled baseline)."""
    from thief_peer.wire import BrainDrivenEngine

    total_survived = 0
    n_games = 20
    seed = 42

    for game_seed in range(n_games):
        a, b = pair("Police", "Thief")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_terms,
            seed=seed + game_seed,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_terms,
            seed=seed + game_seed,
        )
        engine_a = StandInPoliceEngine()
        engine_b = BrainDrivenEngine(Role.THIEF, config=_strategy_config, seed=seed + game_seed)
        result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)
        thief_survived = any(
            row.outcome is Outcome.SURVIVAL and row.role is Role.THIEF
            for row in result_b.ledger
        )
        if thief_survived:
            total_survived += 1

    survival_rate = total_survived / n_games
    print(f"\nKPI vs stand-in (labeled): {total_survived}/{n_games} = {survival_rate:.1%}")
    assert survival_rate >= 0.30, f"Survival rate {survival_rate:.1%} < 30%"
