"""Series-scoped transport composition for the Thief peer."""

from pathlib import Path

from common.domain.scoring import Role
from common.transport.greeting_reply import counter_signed_reply_builder
from common.transport.greetings import NegotiationContext, SeriesGreetingSession
from common.transport.loopback import Inboxes
from common.transport.opponent_pin import OpponentPin
from common.transport.series import PeerFacade, SeriesResume
from common.transport.terms import project_terms
from thief_peer.live_events import observe_driver
from thief_peer.wire.negotiate_per_subgame import negotiated_subgame_driver
from thief_peer.wire.resume import load_sg2_resume


def prepare_series_startup(
    *,
    raw_config: dict,
    private,
    group_id: str,
    role: Role,
    identity_block: dict,
    resume_sg1_dir: Path | str | None,
    resume_sg2_dir: Path | str | None,
) -> tuple[Inboxes, SeriesResume | None]:
    """Compose negotiation inboxes and optional verified recovery state."""
    terms = project_terms(raw_config, private.__dict__)
    terms["num_games"] = 6
    resume = (
        load_sg2_resume(
            resume_sg1_dir,
            terms=terms,
            group_id=group_id,
            locks=None,
            settled_sg2_dir=resume_sg2_dir,
        )
        if resume_sg1_dir is not None
        else None
    )
    inboxes = Inboxes()
    inboxes.agreement_reply = counter_signed_reply_builder(
        terms=terms,
        group_id=group_id,
        natural_role=role,
        identity_block=identity_block,
    )
    return inboxes, resume


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
