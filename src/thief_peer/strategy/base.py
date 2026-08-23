"""BrainBase — shared strategy core with pinned two-phase decide().

Phase order is PINNED (M-04 {#hint_isolation}): the move is selected first
by pure Python — the LLM is NEVER consulted here (NG-003) — and the hint
is produced afterwards; a hint can never influence an already-selected move.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Protocol

from common.domain.board import Cell
from common.domain.scoring import Role

from .decision import Decision
from .hint_types import TokenUsage
from .hints import HintWriter


class BeliefGrid(Protocol):
    """Minimal belief surface consumed by the strategy (FR-B6 queries)."""

    def most_likely(self) -> Cell: ...
    def peak_probability(self) -> float: ...


class BrainBase(ABC):
    """Shared strategy core. Phase order is PINNED (M-04 {#hint_isolation})."""

    role: Role

    def __init__(
        self,
        rng: random.Random | None = None,
        arena: str = "New York",
        max_words: int = 15,
        hint_writer: HintWriter | None = None,
    ) -> None:
        self.rng = rng or random.Random(0)
        self.arena = arena
        self.max_words = max_words
        self.hint_writer = hint_writer or HintWriter(Role.THIEF, self.rng, arena, max_words)
        self.visited: set[Cell] = set()
        self.last_field: dict[str, float] = {}

    def reset(self, start: Cell) -> None:
        """Fresh sub-game: visited = {start}; last_field = {}."""
        self.visited = {start}
        self.last_field = {}

    def note_evidence(self, field: dict[str, float]) -> None:
        """Remember the last received scent field (FR-T2 diffuse-fallback input).

        Called by the C04 turn handler on each received turn, BEFORE decide()
        (SD-T4). The field is evidence, never opponent truth.
        """
        self.last_field = dict(field)

    def decide(
        self,
        state,  # GameEngine
        belief: BeliefGrid,
        opponent_hint: str,
        arena: str,
        deadline: float | None = None,
    ) -> Decision:
        """The pinned two-phase decision (PRD FR-T1…FR-T7).

        1. legal = state.legal_moves(); if legal == ["STAY"]:
           return Decision("STAY", fallback=True)   # capture is domain-decided
        2. action, barrier = self._decide_move(state, belief)   # pure Python
        3. dest = destination of the chosen action; on an orthogonal MOVE:
           visited.add(dest)
        4. hint, verdict = hint_writer.say(dest, deadline=deadline)   # FROM the
           chosen destination, never the pre-move position (hint generation
           can never feed back into move selection — the action above is
           already final).
        5. return Decision(action, barrier, hint, verdict, fallback=False)
        """
        legal = state.legal_moves()
        if legal == ["STAY"]:
            # No hint writer call happened: usage is KNOWN zero, not unknown.
            return Decision("STAY", fallback=True, usage=TokenUsage(0, 0))

        action, barrier = self._decide_move(state, belief)

        # The destination of the ALREADY-SELECTED action. Update visited on
        # orthogonal MOVE only (FR-T8); the hint is generated from this
        # destination below, never from the pre-move position.
        dest = state.board.step(state.position, action) if action != "STAY" else state.position
        if action != "STAY":
            self.visited.add(dest)

        hint, verdict = self.hint_writer.say(dest, deadline=deadline)
        # Read immediately: last_result is per-turn state, valid only until
        # the next say() call. Seals fallback_reason + usage (SEC-009); never
        # exposed on the public turn message (T027). getattr guards a
        # minimal duck-typed HintWriter stand-in lacking last_result.
        sealed = getattr(self.hint_writer, "last_result", None)
        return Decision(
            action=action,
            barrier_cell=barrier,
            hint=hint,
            verdict=verdict,
            fallback=False,
            fallback_reason=sealed.fallback_reason if sealed else None,
            usage=sealed.usage if sealed else None,
        )

    @abstractmethod
    def _decide_move(
        self, state, belief: BeliefGrid
    ) -> tuple[str, Cell | None]:
        """(action, barrier_cell). PURE PYTHON. The LLM is NEVER consulted here."""
        ...
