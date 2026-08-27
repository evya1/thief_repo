"""Series-scoped transport composition for the Thief peer."""

from common.transport.greetings import NegotiationContext, SeriesGreetingSession
from common.transport.opponent_pin import OpponentPin
from common.transport.series import PeerFacade
from thief_peer.live_events import observe_driver
from thief_peer.wire.negotiate_per_subgame import negotiated_subgame_driver


def compose_series_peer(
    *, channel, engine, config, group_id: str, mode: str, audit_wire, listener,
    resume=None,
) -> PeerFacade:
    """Create the one opponent pin and greeting session owned by this series/resume."""
    opponent_pin = OpponentPin(resume.opponent_group_id if resume else None)
    greetings = SeriesGreetingSession(NegotiationContext(
        terms=config.terms,
        group_id=group_id,
        locks=config.locks,
        identity_block=config.identity_block,
    ))
    driver = negotiated_subgame_driver(
        group_id, opponent_pin=opponent_pin, audit_wire=audit_wire,
        skip_sub_games=frozenset({2}) if resume and resume.next_sub_game == 2 else frozenset(),
        greeting_session=greetings,
    )
    return PeerFacade(
        channel=channel,
        engine=engine,
        config=config,
        name=group_id,
        mode=mode,
        opponent_pin=opponent_pin,
        resume=resume,
        greeting_session=greetings,
        subgame_driver=observe_driver(driver, listener),
    )
