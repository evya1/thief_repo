"""Phase 3 / H4: custom BrainBase construction receives only common kwargs.

A custom BrainBase subclass whose constructor accepts only the documented
common dependencies must resolve successfully -- ThiefBrain's private
weight vector (w_dist/w_mob/w_fresh/w_trap/min_confidence) must never be
force-fed to an arbitrary injected class.
"""

from __future__ import annotations

import sys

from common.domain.scoring import Role
from thief_peer.strategy import resolve_brain
from thief_peer.strategy.base import BrainBase


class _FakeModule:
    """A fake module for testing import resolution."""

    def __init__(self) -> None:
        self.__name__ = "test_fake_module"


class TestCustomBrainConstruction:
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
