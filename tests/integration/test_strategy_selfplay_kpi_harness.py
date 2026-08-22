"""KPI harness: run_kpi_series against a police that can actually capture.

TC-T17, rewritten per PR #34 review H5 (the previous "reference" opponents
never placed a barrier and never issued a capture claim, so any policy --
including always-STAY -- passed the old 60%/30% gates). Every required THIEF
sub-game across the series is evaluated (never ``any()``), the thief under
test runs the real coordinator+brain (``BrainDrivenEngine`` running the
actual ``ThiefBrain``, the same composition ``create_peer`` wires in
production), and a mandatory negative control (an always-STAY thief) must
FAIL against the same opponent, with the failure coming from an actual
recorded CAPTURE outcome.
"""

from __future__ import annotations

from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, run_series
from tests.integration.test_strategy_selfplay_kpi import (
    AlwaysStayThiefEngine,
    DummyBudgets,
    GreedyCapturingPolice,
    KPIResult,
    _strategy_config,
    _terms,
)
from thief_peer.wire.brain import BrainDrivenEngine


def _run_against_capturing_police(thief_engine_factory, n_games: int, seed: int) -> KPIResult:
    """Play n_games full series against GreedyCapturingPolice; evaluate EVERY
    THIEF-role sub-game across every game (not any() across the series)."""
    survived = 0
    captured = 0
    capture_rounds: list[int] = []
    total_thief_subgames = 0

    for game_seed in range(n_games):
        a, b = pair("Police", "Thief")
        config_a = PeerConfig(Role.POLICE, DummyBudgets(), _terms, seed=seed + game_seed)
        config_b = PeerConfig(Role.THIEF, DummyBudgets(), _terms, seed=seed + game_seed)

        thief_engine = thief_engine_factory(seed + game_seed)

        def thief_position(_engine=thief_engine) -> tuple[int, int]:
            session = getattr(_engine, "_session", None)
            if session is not None and session.engine is not None:
                return session.engine.position
            return (3, 3)

        police_engine = GreedyCapturingPolice(
            Role.POLICE, seed=seed + game_seed, terms=_terms, thief_position_fn=thief_position,
        )

        _result_a, result_b = run_series(a, b, config_a, config_b, police_engine, thief_engine)

        for row in result_b.ledger:
            if row.role is not Role.THIEF:
                continue
            total_thief_subgames += 1
            if row.outcome is Outcome.SURVIVAL:
                survived += 1
            elif row.outcome is Outcome.CAPTURE:
                captured += 1
                capture_rounds.append(row.steps)

    return KPIResult(
        total_thief_subgames=total_thief_subgames,
        survived=survived,
        captured=captured,
        capture_rounds=capture_rounds,
    )


def test_kpi_vs_capturing_police() -> None:
    """TC-T17: survival vs a police opponent CAPABLE OF CAPTURING >= 60%, evaluated
    over every required THIEF sub-game (not any() over the series)."""
    result = _run_against_capturing_police(
        lambda seed: BrainDrivenEngine(Role.THIEF, config=_strategy_config, seed=seed),
        n_games=15, seed=42,
    )
    rate = result.survived / result.total_thief_subgames
    print(f"\nThiefBrain vs capturing police: {result.survived}/{result.total_thief_subgames} = {rate:.1%}")
    assert result.total_thief_subgames >= 15  # sanity: every game contributed sub-games
    assert rate >= 0.60, f"survival rate {rate:.1%} < 60%"


def test_kpi_negative_control_always_stay_fails() -> None:
    """Mandatory negative control: an always-STAY thief must FAIL this KPI, and the
    failure must come from an ACTUAL recorded capture, not from recognizing the class."""
    result = _run_against_capturing_police(
        lambda seed: AlwaysStayThiefEngine(Role.THIEF, seed=seed),
        n_games=8, seed=42,
    )
    rate = result.survived / result.total_thief_subgames
    print(f"\nalways-STAY vs capturing police: {result.survived}/{result.total_thief_subgames} = {rate:.1%}")
    assert result.captured > 0, "the negative control must actually be captured, not merely score low"
    assert rate < 0.60, f"always-STAY unexpectedly passed the KPI at {rate:.1%}"
