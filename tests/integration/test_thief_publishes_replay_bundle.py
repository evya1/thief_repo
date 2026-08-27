"""The thief runner must publish the internal replay bundle, not just a result summary.

The runner delegates artifact policy to ``reporting.runtime_artifacts``; that boundary must
still publish a replay for every settled result.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from thief_peer.reporting.replay_bundle import publish_replay_bundle
from thief_peer.sdk import Budgets, create_peer, verify_replay_bundle


@pytest.fixture(scope="module")
def settled_series() -> SeriesResult:
    config = Path(__file__).resolve().parents[2] / "config" / "game.json"
    channel_a, channel_b = pair("rb-police", "rb-thief")
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(config, channel=channel_a, role=Role.POLICE, group_id="rb-police",
                         budgets=budgets)
    thief = create_peer(config, channel=channel_b, role=Role.THIEF, group_id="rb-thief",
                        budgets=budgets)
    out: dict[str, SeriesResult] = {}
    errors: list[Exception] = []

    def go(name: str, facade: PeerFacade) -> None:
        try:
            out[name] = facade.run()
        except Exception as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=go, args=("p", police)),
               threading.Thread(target=go, args=("t", thief))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    assert out["t"].settled
    return out["t"]


def test_the_thief_side_publishes_a_full_internal_bundle(settled_series, tmp_path):
    bundle = publish_replay_bundle(tmp_path, settled_series)
    members = sorted(p.name for p in bundle.iterdir())
    assert len(members) == 15, members
    assert bundle.parent.name == "replay"


def test_the_published_thief_bundle_verifies(settled_series, tmp_path):
    bundle = publish_replay_bundle(tmp_path, settled_series)
    report = verify_replay_bundle(bundle)
    assert report.verdict.value == "verified_ok"
    assert report.coverage.integrity is True


def test_the_runner_wires_publication_rather_than_only_a_summary():
    """A regression guard on the wiring itself, not on the bundle module."""
    import inspect

    from thief_peer import runner
    from thief_peer.reporting import runtime_artifacts

    runner_source = inspect.getsource(runner.run_one_peer)
    artifact_source = inspect.getsource(runtime_artifacts.write_series_artifacts)
    assert "write_series_artifacts(" in runner_source
    assert "publish_replay_bundle(" in artifact_source
    assert "publish_kit(" in runner_source
