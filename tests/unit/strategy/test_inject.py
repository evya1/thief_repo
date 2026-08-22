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
from thief_peer.strategy.thief import ThiefBrain


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


class TestCustomBrainConstruction:
    """Phase 3 / H4: a custom BrainBase subclass whose constructor accepts only the
    documented common dependencies must resolve successfully -- ThiefBrain's private
    weight vector (w_dist/w_mob/w_fresh/w_trap/min_confidence) must never be force-fed
    to an arbitrary injected class.
    """

    def test_custom_brain_with_only_common_kwargs_succeeds(self) -> None:
        fake = _FakeModule()

        class CommonOnlyBrain(BrainBase):
            """Accepts ONLY the documented common constructor dependencies."""

            def __init__(self, rng, arena, max_words, hint_writer) -> None:
                super().__init__(rng=rng, arena=arena, max_words=max_words, hint_writer=hint_writer)

            def _decide_move(self, state, belief):
                return "STAY", None

        fake.CommonOnlyBrain = CommonOnlyBrain
        sys.modules["test_common_only_module"] = fake
        try:
            config = {
                "seed": 7,
                "world": {"map_area": "New York", "hint_max_words": 15},
                "strategy": {"thief_class": "test_common_only_module:CommonOnlyBrain"},
            }
            brain = resolve_brain(config, Role.THIEF)
            assert isinstance(brain, CommonOnlyBrain)
            assert brain.arena == "New York"
            assert brain.max_words == 15
        finally:
            del sys.modules["test_common_only_module"]

    def test_custom_brain_never_receives_thief_only_weights(self) -> None:
        """A custom class that does NOT declare w_dist/etc must not blow up, and must
        never see ThiefBrain's weight kwargs -- proving H4 is fixed, not just untested."""
        fake = _FakeModule()
        received: dict[str, object] = {}

        class RecordingBrain(BrainBase):
            def __init__(self, **kwargs) -> None:
                received.update(kwargs)
                super().__init__(
                    rng=kwargs["rng"], arena=kwargs["arena"],
                    max_words=kwargs["max_words"], hint_writer=kwargs["hint_writer"],
                )

            def _decide_move(self, state, belief):
                return "STAY", None

        fake.RecordingBrain = RecordingBrain
        sys.modules["test_recording_module"] = fake
        try:
            config = {
                "seed": 1,
                "world": {"map_area": "New York", "hint_max_words": 15},
                "strategy": {
                    "thief_class": "test_recording_module:RecordingBrain",
                    # Even if a weights section is present, it must not leak through.
                    "thief": {"w_dist": 99.0, "w_trap": 99.0},
                },
            }
            resolve_brain(config, Role.THIEF)
            assert "w_dist" not in received
            assert "w_trap" not in received
            assert "min_confidence" not in received
            assert set(received) == {"rng", "arena", "max_words", "hint_writer"}
        finally:
            del sys.modules["test_recording_module"]
