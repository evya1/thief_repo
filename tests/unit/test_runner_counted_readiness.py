"""The production runner must enforce counted readiness before transport starts."""

import pytest

from thief_peer import runner


def test_counted_runner_refuses_before_starting_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner, "serve_background",
        lambda *a, **k: pytest.fail("transport started before counted readiness passed"),
    )
    assert runner.run_one_peer(mode="counted") == 2
