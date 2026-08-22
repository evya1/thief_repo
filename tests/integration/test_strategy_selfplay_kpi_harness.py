"""KPI harness: run_kpi_series against a police that can actually capture.

TC-T17, rewritten per PR #34 review H5 (the previous "reference" opponents
never placed a barrier and never issued a capture claim, so any policy --
including always-STAY -- passed the old 60%/30% gates). Every required THIEF
sub-game across the series is evaluated (never ``any()``), the thief under
test runs the real coordinator+brain (``BrainDrivenEngine`` running the
actual ``ThiefBrain``), and a mandatory negative control (an always-STAY
thief) must FAIL against the same opponent, with the failure coming from an
actual recorded CAPTURE outcome.

The strategy configuration is no longer hand-written here (LOW-11): it is
``production_strategy_config()``, obtained by asking ``create_peer`` for a
peer and reading the mapping that factory hands its engine, so this KPI
measures the configuration this repository actually ships.
``test_kpi_thief_config_is_the_production_composition`` pins that provenance.
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
    _terms,
)
from thief_peer.sdk import create_peer
from thief_peer.wire.brain import BrainDrivenEngine

#: The configuration this repository actually ships with.
_SHARED_CONFIG_PATH = "config/game.json"
_PRIVATE_CONFIG_PATH = "config/game.toml.example"


def production_strategy_config() -> dict:
    """The Thief strategy config assembled by the PRODUCTION composition root.

    LOW-11: this used to be a hand-written two-key dict, so the KPI could keep
    reporting a healthy number while the shipped configuration drifted away
    from it -- different weights, a brain override, another scent model -- with
    nothing failing. It is obtained through ``create_peer`` instead: the same
    shared-JSON + private-TOML -> ``assemble_strategy_config`` path production
    uses, read off the engine that factory wires.
    """
    peer = create_peer(
        _SHARED_CONFIG_PATH, private_config_path=_PRIVATE_CONFIG_PATH, role=Role.THIEF,
    )
    return dict(peer.engine.config)


_strategy_config = production_strategy_config()


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


def test_kpi_thief_config_is_the_production_composition() -> None:
    """LOW-11: the KPI's thief config is the SHIPPED one, not a hand-written stub.

    Pins the production composition path end-to-end: ``create_peer`` with no
    explicit ``strategy=`` wires a ``BrainDrivenEngine``, and the exact mapping
    it hands that engine is the mapping every KPI run above uses.
    """
    peer = create_peer(
        _SHARED_CONFIG_PATH, private_config_path=_PRIVATE_CONFIG_PATH, role=Role.THIEF,
    )
    assert type(peer.engine).__name__ == "BrainDrivenEngine"
    assert peer.engine.config == _strategy_config

    # Not a stub: it carries the assembled strategy weights and the pinned scent
    # model, both of which the previous two-key hand-written dict omitted.
    assert _strategy_config["strategy"]["thief"]["w_trap"] == 5.0
    assert _strategy_config["scent_model"]
    assert _strategy_config["world"]["map_area"]
