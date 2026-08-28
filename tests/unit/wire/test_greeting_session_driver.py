"""Series greeting session regressions at the Thief recovery/driver boundary."""

import pytest

from common.domain.scoring import Role
from common.transport.greetings import ConflictingGreetingError
from common.transport.integrity import new_nonce
from common.transport.loopback import pair
from common.transport.negotiate import our_greeting
from common.transport.series import PeerConfig
from tests.unit.wire.test_negotiate_per_subgame import (
    _BUDGETS,
    _TERMS,
    _config,
    _negotiate,
    _stub_inner,
)
from thief_peer.wire.negotiate_per_subgame import negotiated_subgame_driver


def test_driver_rejects_a_different_configuration_before_inner_game() -> None:
    ch_a, _ = pair("A", "B")
    calls: list[int] = []
    driver = negotiated_subgame_driver("A", inner=_stub_inner(calls))
    driver(ch_a, None, _config(Role.THIEF), 1)
    changed = PeerConfig(
        natural_role=Role.THIEF, budgets=_BUDGETS,
        terms={**_TERMS, "setting": "Akko"}, locks={},
    )

    with pytest.raises(ConflictingGreetingError, match="different configuration"):
        driver(ch_a, None, changed, 1)
    assert calls == [1]


def test_recovery_skips_accepted_g2_and_discards_stale_g2_before_g3() -> None:
    ch_a, ch_b = pair("A", "B")
    calls: list[int] = []
    driver = negotiated_subgame_driver(
        "A", inner=_stub_inner(calls), skip_sub_games=frozenset({2}),
    )
    driver(ch_a, None, _config(Role.THIEF), 2)
    ch_b.send_agreement(our_greeting(
        terms=_TERMS, nonce=new_nonce(), group_id="B", role=Role.THIEF.value,
        sub_game_number=2,
    ))

    sent = _negotiate(driver, ch_a, ch_b, 3, opp_role=Role.POLICE.value)

    assert calls == [2, 3]
    assert sent["sub_game_number"] == 3
