"""Injection seam tests: resolve_brain_cls and resolve_brain.

TC-T12: explicit thief_class selector loads custom class end-to-end;
        malformed selector => ValueError; missing attribute => ValueError;
        non-BrainBase target => TypeError; unset selector => shipped ThiefBrain.
"""

from __future__ import annotations

import random
import sys

import pytest

from common.domain.scoring import Role
from thief_peer.strategy import resolve_brain, resolve_brain_cls
from thief_peer.strategy.base import BrainBase
from thief_peer.strategy.hint_types import ProviderReply, TokenUsage
from thief_peer.strategy.thief import ThiefBrain


class _FakeProvider:
    """Minimal TextProvider stand-in (structural, no live call)."""

    def render(self, request, *, deadline=None):
        return ProviderReply(text="ok", usage=TokenUsage(0, 0), provider="fake", model="fake")


class _FakeModule:
    """A fake module for testing import resolution."""

    def __init__(self) -> None:
        self.__name__ = "test_fake_module"


class TestResolveBrainCls:
    """TC-T12: injection seam fail-fast behavior."""

    def test_unset_selector_returns_thief_brain(self) -> None:
        cls = resolve_brain_cls(None, Role.THIEF)
        assert cls is ThiefBrain

    def test_empty_config_returns_thief_brain(self) -> None:
        cls = resolve_brain_cls({}, Role.THIEF)
        assert cls is ThiefBrain

    def test_malformed_selector_value_error(self) -> None:
        config = {"strategy": {"thief_class": "no_colon"}}
        with pytest.raises(ValueError, match="malformed"):
            resolve_brain_cls(config, Role.THIEF)

    def test_missing_module_value_error(self) -> None:
        config = {"strategy": {"thief_class": "nonexistent_module:SomeClass"}}
        with pytest.raises(ValueError, match="not found"):
            resolve_brain_cls(config, Role.THIEF)

    def test_missing_class_value_error(self) -> None:
        # Use a real module but missing class.
        config = {"strategy": {"thief_class": "os:NonExistentClass"}}
        with pytest.raises(ValueError, match="not found"):
            resolve_brain_cls(config, Role.THIEF)

    def test_non_brainbase_type_error(self) -> None:
        config = {"strategy": {"thief_class": "os:path"}}
        with pytest.raises(TypeError, match="not a BrainBase subclass"):
            resolve_brain_cls(config, Role.THIEF)

    def test_custom_class_loaded(self) -> None:
        """Register a fake module with a BrainBase subclass."""
        fake = _FakeModule()

        class CustomBrain(BrainBase):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def _decide_move(self, state, belief):
                return "MOVE:S", None

        fake.CustomBrain = CustomBrain
        sys.modules["test_fake_module"] = fake

        try:
            config = {"strategy": {"thief_class": "test_fake_module:CustomBrain"}}
            cls = resolve_brain_cls(config, Role.THIEF)
            assert cls is CustomBrain
            assert issubclass(cls, BrainBase)
        finally:
            del sys.modules["test_fake_module"]

    def test_police_selector_ignored_for_thief(self) -> None:
        config = {"strategy": {"police_class": "os:path"}}
        cls = resolve_brain_cls(config, Role.THIEF)
        assert cls is ThiefBrain


class TestResolveBrain:
    """TC-T12 end-to-end: resolve_brain instantiates with correct params."""

    def test_default_thief_brain(self) -> None:
        config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.THIEF)
        assert isinstance(brain, ThiefBrain)
        assert brain.arena == "New York"
        assert brain.max_words == 15

    def test_custom_weights(self) -> None:
        config = {
            "seed": 42,
            "world": {"map_area": "New York", "hint_max_words": 10},
            "strategy": {
                "thief": {
                    "w_dist": 2.0,
                    "w_mob": 0.5,
                    "w_fresh": 0.3,
                    "w_trap": 10.0,
                    "min_confidence": 0.25,
                }
            },
        }
        brain = resolve_brain(config, Role.THIEF)
        assert isinstance(brain, ThiefBrain)
        assert brain.w_dist == 2.0
        assert brain.w_mob == 0.5
        assert brain.w_fresh == 0.3
        assert brain.w_trap == 10.0
        assert brain.min_confidence == 0.25

    def test_custom_seed(self) -> None:
        config = {"seed": 99, "world": {"map_area": "New York", "hint_max_words": 15}}
        rng = random.Random(99)
        brain = resolve_brain(config, Role.THIEF, rng=rng)
        assert isinstance(brain, ThiefBrain)

    def test_no_config_uses_defaults(self) -> None:
        brain = resolve_brain(None, Role.THIEF)
        assert isinstance(brain, ThiefBrain)
        assert brain.w_dist == 1.0
        assert brain.min_confidence == 0.15

    def test_police_raises(self) -> None:
        """thief_repo has no default POLICE brain (SD-T7)."""
        with pytest.raises(ValueError, match="no default brain class"):
            resolve_brain(None, Role.POLICE)


class TestResolveBrainLLM:
    """F-14: the declared `llm` seam must be used, or rejected fail-fast --
    never silently ignored.
    """

    _config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}

    def test_llm_is_passed_into_hint_writer(self) -> None:
        provider = _FakeProvider()
        brain = resolve_brain(self._config, Role.THIEF, llm=provider)
        assert brain.hint_writer.provider is provider

    def test_no_llm_defaults_to_none(self) -> None:
        brain = resolve_brain(self._config, Role.THIEF)
        assert brain.hint_writer.provider is None

    def test_non_provider_llm_rejected_fail_fast(self) -> None:
        with pytest.raises(TypeError, match="TextProvider"):
            resolve_brain(self._config, Role.THIEF, llm=object())
