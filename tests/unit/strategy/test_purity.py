"""Purity tests: the strategy module imports no transport, wire, or GUI code.

TC-T14: no import of opponent-truth symbols in strategy/; no parameter or
field accepts the opponent's position.
"""

from __future__ import annotations


class TestImportPurity:
    """The strategy module and its submodules import no transport or wire code."""

    def test_decision_no_transport_imports(self) -> None:
        import thief_peer.strategy.decision as mod
        for name in dir(mod):
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ is not None:
                assert "transport" not in obj.__module__, f"imports transport via {obj.__module__}"
                assert "wire" not in obj.__module__, f"imports wire via {obj.__module__}"

    def test_base_no_transport_imports(self) -> None:
        import thief_peer.strategy.base as mod
        for name in dir(mod):
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ is not None:
                assert "transport" not in obj.__module__, f"imports transport via {obj.__module__}"
                assert "wire" not in obj.__module__, f"imports wire via {obj.__module__}"

    def test_hints_no_transport_imports(self) -> None:
        import thief_peer.strategy.hints as mod
        for name in dir(mod):
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ is not None:
                assert "transport" not in obj.__module__, f"imports transport via {obj.__module__}"
                assert "wire" not in obj.__module__, f"imports wire via {obj.__module__}"

    def test_inject_no_transport_imports(self) -> None:
        import thief_peer.strategy.inject as mod
        for name in dir(mod):
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ is not None:
                assert "transport" not in obj.__module__, f"imports transport via {obj.__module__}"
                assert "wire" not in obj.__module__, f"imports wire via {obj.__module__}"

    def test_thief_no_transport_imports(self) -> None:
        import thief_peer.strategy.thief as mod
        for name in dir(mod):
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ is not None:
                assert "transport" not in obj.__module__, f"imports transport via {obj.__module__}"
                assert "wire" not in obj.__module__, f"imports wire via {obj.__module__}"


class TestNoOpponentTruthLeakage:
    """TC-T14: no parameter or field accepts the opponent's position."""

    def test_decision_no_position_field(self) -> None:
        from thief_peer.strategy.decision import Decision
        fields = Decision.__dataclass_fields__
        for name in fields:
            assert name not in ("opponent_position", "opponent_role", "opponent_state"), (
                f"Decision has opponent-truth field: {name}"
            )

    def test_brainbase_no_opponent_position_param(self) -> None:
        """BrainBase.decide() signature does not accept opponent position."""
        import inspect

        from thief_peer.strategy.base import BrainBase
        sig = inspect.signature(BrainBase.decide)
        params = list(sig.parameters.keys())
        for p in params:
            assert "opponent_pos" not in p.lower(), f"decide has opponent position param: {p}"
            assert "opponent_cell" not in p.lower(), f"decide has opponent cell param: {p}"

    def test_thiefbrain_no_opponent_position_param(self) -> None:
        """ThiefBrain._decide_move() signature does not accept opponent position."""
        import inspect

        from thief_peer.strategy.thief import ThiefBrain
        sig = inspect.signature(ThiefBrain._decide_move)
        params = list(sig.parameters.keys())
        for p in params:
            assert "opponent_pos" not in p.lower(), f"_decide_move has opponent param: {p}"
            assert "opponent_cell" not in p.lower(), f"_decide_move has opponent param: {p}"
