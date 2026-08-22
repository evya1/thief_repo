"""Injection seam: config-selected brain, fail-fast.

Shared core (mirrors police_repo identically modulo import path and role constant).
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from importlib import import_module

from common.domain.scoring import Role

from .base import BrainBase
from .thief import ThiefBrain

_SELECTORS: dict[Role, str] = {
    Role.THIEF: "thief_class",
    Role.POLICE: "police_class",
}


def resolve_brain_cls(
    config: Mapping[str, object] | None, role: Role
) -> type[BrainBase]:
    """The config selector ([strategy] thief_class / police_class, dotted
    "package.module:ClassName") if set, else the shipped default for `role`
    (thief_repo: ThiefBrain; the opposite-role default is PLAN SD-T7).

    Fail-fast: ValueError on malformed selector / missing attribute; TypeError
    if the target is not a BrainBase subclass.
    """
    if config is None:
        return _default_cls(role)
    selector_key = _SELECTORS[role]
    strategy = config.get("strategy")
    if not isinstance(strategy, Mapping):
        return _default_cls(role)
    selector = strategy.get(selector_key)
    if selector is None:
        return _default_cls(role)
    if not isinstance(selector, str) or ":" not in selector:
        raise ValueError(f"malformed brain selector {selector!r} for {role}")
    module_path, class_name = selector.rsplit(":", 1)
    try:
        mod = import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(f"brain module {module_path!r} not found for {role}") from exc
    cls = getattr(mod, class_name, None)
    if cls is None:
        raise ValueError(f"brain class {class_name!r} not found in {module_path}")
    if not (isinstance(cls, type) and issubclass(cls, BrainBase)):
        raise TypeError(f"{class_name} is not a BrainBase subclass")
    return cls


def resolve_brain(
    config: Mapping[str, object] | None,
    role: Role,
    llm: object | None = None,
    rng: random.Random | None = None,
) -> BrainBase:
    """Instantiate the resolved class with the DOCUMENTED common dependencies only.

    Every brain — built-in or custom — receives exactly the constructor
    dependencies the shared core documents: ``rng`` (default: seeded from the
    resolved config's seed), ``arena`` + ``max_words`` from the resolved
    config, and the template ``HintWriter``. ThiefBrain's private weight
    vector (``w_dist``/``w_mob``/``w_fresh``/``w_trap``/``min_confidence``) is
    an explicit *additional* branch that fires ONLY when the resolved class
    is the built-in ``ThiefBrain`` (or a subclass of it) — it is never
    force-fed to an arbitrary injected class (H4). There is no
    ``inspect.signature`` probing and no catch-`TypeError`-and-retry: the
    two construction paths are explicit, not guessed.
    """
    cls = resolve_brain_cls(config, role)
    if rng is None:
        seed = 0
        if config is not None:
            seed = int(config.get("seed", 0))
        rng = random.Random(seed)

    arena = "New York"
    max_words = 15
    if config is not None:
        world = config.get("world")
        if isinstance(world, Mapping):
            arena = str(world.get("map_area", "New York"))
            max_words = int(world.get("hint_max_words", 15))

    from .hints import HintWriter

    hint_writer = HintWriter(role, rng, arena, max_words)
    common_kwargs: dict[str, object] = {
        "rng": rng,
        "arena": arena,
        "max_words": max_words,
        "hint_writer": hint_writer,
    }

    if isinstance(cls, type) and issubclass(cls, ThiefBrain):
        return cls(**common_kwargs, **_thief_weights(config, role))
    return cls(**common_kwargs)


def _thief_weights(config: Mapping[str, object] | None, role: Role) -> dict[str, float]:
    """The built-in ThiefBrain's private weight vector (PRD §9) ONLY.

    Read from the resolved ``[strategy.<role>]`` config mapping; defaults are
    the PLANQ-008 approval baseline. This is never applied to a non-ThiefBrain
    class (H4) -- see ``resolve_brain``.
    """
    role_key = role.value if isinstance(role, Role) else str(role)
    role_cfg: object = {}
    if config is not None:
        strategy = config.get("strategy", {})
        if isinstance(strategy, Mapping):
            role_cfg = strategy.get(role_key, {})
    if not isinstance(role_cfg, Mapping):
        role_cfg = {}
    return {
        "w_dist": float(role_cfg.get("w_dist", 1.0)),
        "w_mob": float(role_cfg.get("w_mob", 0.25)),
        "w_fresh": float(role_cfg.get("w_fresh", 0.15)),
        "w_trap": float(role_cfg.get("w_trap", 5.0)),
        "min_confidence": float(role_cfg.get("min_confidence", 0.15)),
    }


def _default_cls(role: Role) -> type[BrainBase]:
    """Return the shipped default brain class for the role."""
    if role is Role.THIEF:
        return ThiefBrain
    # POLICE default: stand-in kept on this repo (SD-T7).
    raise ValueError(f"no default brain class for {role} in thief_repo")
