"""Two-peer negotiation recovery at an accepted sub-game boundary."""

from __future__ import annotations

import threading
from copy import deepcopy
from types import SimpleNamespace

from common.domain.scoring import Role
from common.transport.integrity import new_nonce
from common.transport.loopback import pair
from common.transport.negotiate import our_greeting
from common.transport.opponent_pin import OpponentPin
from common.transport.series import PeerConfig
from thief_peer.wire.negotiate_per_subgame import negotiated_subgame_driver

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
    "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
    "barriers_max": 14, "setting": "Haifa", "hint_max_words": 15,
    "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}
_BUDGETS = SimpleNamespace(turn_timeout=5.0, connect_timeout=2.0, poll_interval=0.005)


def _config(role: Role) -> PeerConfig:
    return PeerConfig(role, _BUDGETS, deepcopy(_TERMS), locks={})


def _inner(calls: list[int]):
    def run(channel, engine, config, sub_game, *, evidence_sink=None):
        calls.append(sub_game)
        return object()

    return run


def test_resume_skips_accepted_g2_and_stale_material_cannot_become_g3() -> None:
    police_channel, thief_channel = pair("police", "thief")
    police_sent: list[dict] = []
    thief_sent: list[dict] = []
    police_send = police_channel.send_agreement
    thief_send = thief_channel.send_agreement
    police_channel.send_agreement = lambda message: (
        police_sent.append(deepcopy(message)), police_send(message)
    )[1]
    thief_channel.send_agreement = lambda message: (
        thief_sent.append(deepcopy(message)), thief_send(message)
    )[1]
    police_calls: list[int] = []
    thief_calls: list[int] = []
    police_driver = negotiated_subgame_driver(
        "police", inner=_inner(police_calls), opponent_pin=OpponentPin("thief"),
    )
    recovered_thief = negotiated_subgame_driver(
        "thief", inner=_inner(thief_calls), opponent_pin=OpponentPin("police"),
        skip_sub_games=frozenset({2}),
    )

    recovered_thief(thief_channel, None, _config(Role.THIEF), 2)
    assert thief_calls == [2]
    assert thief_sent == []
    police_send(our_greeting(
        terms=_TERMS, nonce=new_nonce(), group_id="police", role="thief",
        sub_game_number=2, opponent_group="thief",
    ))

    errors: list[Exception] = []

    def run(driver, channel, config) -> None:
        try:
            driver(channel, None, config, 3)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=run, args=(police_driver, police_channel, _config(Role.POLICE))),
        threading.Thread(target=run, args=(recovered_thief, thief_channel, _config(Role.THIEF))),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert police_calls == [3]
    assert thief_calls == [2, 3]
    assert [message["sub_game_number"] for message in police_sent] == [3]
    assert [message["sub_game_number"] for message in thief_sent] == [3]
    assert police_sent[0]["role"] == "police"
    assert thief_sent[0]["role"] == "thief"
