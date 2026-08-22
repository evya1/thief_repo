"""Normalized private ``[strategy]`` settings — one typed record, not a dict.

Split out of ``wire/config.py`` (line cap) but part of the same startup
normalization boundary: raw TOML shape is parsed exactly once, here, into
``StrategySettings``; nothing downstream (the brain, the inject seam, the
wire adapters) re-parses ``[strategy]`` / ``[strategy.thief]`` for itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thief_peer.wire.config import PrivateConfig


@dataclass(frozen=True, slots=True)
class StrategySettings:
    """Normalized ``[strategy]`` / ``[strategy.<role>]`` private config (FR-T9, §9)."""

    thief_class: str | None = None
    thief_weights: dict[str, float] = field(default_factory=dict)
    trash_talk: dict[str, object] = field(default_factory=dict)


def load_strategy_settings(toml_data: dict) -> StrategySettings:
    """Parse the raw ``[strategy]`` TOML table into a ``StrategySettings`` record."""
    strategy = toml_data.get("strategy", {})
    if not isinstance(strategy, dict):
        return StrategySettings()
    thief_class = strategy.get("thief_class")
    thief_section = strategy.get("thief", {})
    weights = (
        {k: float(v) for k, v in thief_section.items()}
        if isinstance(thief_section, dict)
        else {}
    )
    trash = toml_data.get("trash_talk", {})
    return StrategySettings(
        thief_class=str(thief_class) if thief_class is not None else None,
        thief_weights=weights,
        trash_talk=trash if isinstance(trash, dict) else {},
    )


def assemble_strategy_config(
    private: PrivateConfig, shared: dict[str, Any], seed: int = 0,
) -> dict[str, Any]:
    """Build the ``resolve_brain``-shaped mapping from validated shared JSON + private TOML.

    ONE place assembles this shape (``{"seed", "world", "strategy": {...},
    "scent_model": ...}``) instead of every call site hand-building a nested
    dict; ``resolve_brain`` and the wire adapters both consume this, and no
    strategy module reads a config file or global state itself.
    """
    world = shared.get("world", {}) if isinstance(shared, dict) else {}
    strategy_cfg: dict[str, Any] = {"thief": dict(private.strategy.thief_weights)}
    if private.strategy.thief_class:
        strategy_cfg["thief_class"] = private.strategy.thief_class
    return {
        "seed": seed or private.seed,
        "world": {
            "map_area": world.get("map_area", "New York"),
            "hint_max_words": world.get("hint_max_words", 15),
        },
        "strategy": strategy_cfg,
        "trash_talk": dict(private.strategy.trash_talk),
        "scent_model": private.scent_model,
    }
