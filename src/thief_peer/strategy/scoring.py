"""Pure move-ranking core for the Thief evasion policy (FR-T2/FR-T3, M-04).

Extracted out of ``ThiefBrain`` so the ranking is testable as plain data in
and plain data out: no opponent truth, no mutation of the caller's
``visited`` set, no I/O, no LLM. Everything this module needs is passed in
explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.domain.board import ORTHOGONAL, Board, Cell, manhattan


@dataclass(frozen=True, slots=True)
class ThiefWeights:
    """Score weights for the evasion ranking (PRD §9, PLANQ-008 baseline)."""

    w_dist: float = 1.0
    w_mob: float = 0.25
    w_fresh: float = 0.15
    w_trap: float = 5.0


def orthogonal_mobility(board: Board, cell: Cell, barriers: list[Cell]) -> int:
    """Count legal orthogonal moves from ``cell`` explicitly (never ``len(legal) - 1``)."""
    blocked = set(barriers)
    return sum(
        1
        for move in ORTHOGONAL
        if board.in_bounds(board.step(cell, move)) and board.step(cell, move) not in blocked
    )


def destination(board: Board, position: Cell, action: str) -> Cell:
    """The cell an action lands on; ``STAY`` never moves."""
    return position if action == "STAY" else board.step(position, action)


def select_thief_action(
    *,
    board: Board,
    position: Cell,
    barriers: list[Cell],
    legal_moves: list[str],
    threat: Cell,
    visited: frozenset[Cell],
    weights: ThiefWeights,
    confident_threat_cell: Cell | None,
) -> str:
    """Score every legal action and return the CT-01 first-maximum winner.

    Pure: does not mutate ``visited`` or ``barriers`` and performs no I/O.

    A hard safety constraint precedes scoring (M-04 H2): when the belief is
    confident (``confident_threat_cell`` is not ``None``), any orthogonal
    action landing exactly on that cell is excluded from consideration
    whenever a safe legal alternative exists, so no combination of mobility
    or freshness weight can outbid one unit of distance onto a cell the
    policy is confident the Police occupies.
    """
    candidates = legal_moves
    if confident_threat_cell is not None:
        safe = [
            action
            for action in legal_moves
            if destination(board, position, action) != confident_threat_cell
        ]
        if safe:
            candidates = safe

    size = board.size
    best_action = candidates[0]
    best_score = float("-inf")
    for action in candidates:
        dest = destination(board, position, action)
        d = manhattan(dest, threat)
        mobility = orthogonal_mobility(board, dest, barriers)
        fresh = 1 if (action != "STAY" and dest not in visited) else 0
        trap = 1 if board.boxed_in(dest, barriers) else 0
        score = (
            weights.w_dist * d / size
            + weights.w_mob * mobility / 4
            + weights.w_fresh * fresh
            - weights.w_trap * trap
        )
        if score > best_score:
            best_score = score
            best_action = action

    return best_action
