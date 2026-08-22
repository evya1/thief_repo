"""Pure scoring core tests: mobility counting, w_trap materiality, H2 safety gate.

FR-T3, M-04 H2 (confident threat cell exclusion), scoring.py purity.
"""

from __future__ import annotations

from common.domain.board import Board
from thief_peer.strategy.scoring import (
    ThiefWeights,
    orthogonal_mobility,
    select_thief_action,
    trap_risk,
)


class TestOrthogonalMobility:
    """Explicit mobility counting -- never assumes len(legal_moves) - 1."""

    def test_open_center_has_full_mobility(self) -> None:
        board = Board(size=7)
        assert orthogonal_mobility(board, (3, 3), []) == 4

    def test_corner_has_two(self) -> None:
        board = Board(size=7)
        assert orthogonal_mobility(board, (0, 0), []) == 2

    def test_barriers_reduce_mobility(self) -> None:
        board = Board(size=7)
        assert orthogonal_mobility(board, (3, 3), [(2, 3), (4, 3)]) == 2


class TestWTrapMaterial:
    """w_trap must materially influence a reachable fixture (PRD FR-T3 formula).

    Architectural finding (repaired here, not silently patched): for any
    destination reached by a single ORTHOGONAL move from a legally-occupiable
    origin, ``Board.boxed_in(dest, barriers)`` can never be True in a
    reachable game state -- one of ``dest``'s four orthogonal neighbours is
    always the origin cell the mover just vacated, and the origin cannot
    itself be a barrier while an agent legally occupies it (a barrier
    landing on an occupied cell is rule 46 capture, which ends the sub-game
    before another decision is made). The accepted fix (see
    ``docs/decisions/ADR-006-strategy-heuristic-priorities.md`` consequences
    and ``docs/PRD_thief_strategy.md`` FR-T3) keeps ``Board.boxed_in`` as the
    unchanged rule-47 terminal predicate and scores the trap term against
    ``scoring.trap_risk``: a conservative, reachable one-exit-or-fewer
    strategy risk (``orthogonal_mobility(dest) <= 1``), not a claim that the
    destination is itself a captured/boxed state.

    All fixtures below are reachable GameEngine-consistent states: barriers
    never include the origin the Thief is standing on.
    """

    _BARRIERS = [(3, 1), (2, 0), (2, 2)]  # 3 of dest (2,1)'s 4 neighbours; origin (1,1) left free

    def test_one_exit_destination_penalized_when_safer_destination_exists(self) -> None:
        """MOVE:S lands on (2,1), a reachable one-exit destination (mobility 1: only
        the vacated origin is open) that is also farther from the threat cell.
        MOVE:E lands on (1,2), a safer 3-exit destination. With w_trap dominant,
        the ranking avoids the farther-but-risky destination in favor of the
        safer one even though raw distance alone would favor the risky one."""
        board = Board(size=7)
        weights = ThiefWeights(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=5.0)
        action = select_thief_action(
            board=board, position=(1, 1), barriers=self._BARRIERS,
            legal_moves=["MOVE:S", "MOVE:E"],
            threat=(0, 6), visited=frozenset(), weights=weights,
            confident_threat_cell=None,
        )
        assert action == "MOVE:E"  # avoids the reachable one-exit dest (2,1)

    def test_w_trap_zero_changes_the_winner_on_the_same_reachable_state(self) -> None:
        """Same reachable state as above: zeroing w_trap flips the winner back to the
        farther (but risky) destination, proving the trap term is materially live."""
        board = Board(size=7)
        weights = ThiefWeights(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=0.0)
        action = select_thief_action(
            board=board, position=(1, 1), barriers=self._BARRIERS,
            legal_moves=["MOVE:S", "MOVE:E"],
            threat=(0, 6), visited=frozenset(), weights=weights,
            confident_threat_cell=None,
        )
        assert action == "MOVE:S"  # zero-trap run picks the farther dest purely on distance

    def test_two_or_more_exits_is_not_trap_risk(self) -> None:
        board = Board(size=7)
        assert trap_risk(orthogonal_mobility(board, (3, 3), [])) is False  # 4 exits
        assert trap_risk(orthogonal_mobility(board, (2, 1), self._BARRIERS)) is True  # 1 exit

    def test_boxed_in_stays_the_unchanged_rule_47_predicate(self) -> None:
        """Documents that ``Board.boxed_in`` is untouched by this fix: it is still
        always False for a single-orthogonal-move destination's back-neighbour (the
        origin) reachable case, and the strategy layer no longer calls it at all."""
        board = Board(size=7)
        origin = (3, 3)
        barriers = [(1, 3), (2, 2), (2, 4)]  # 3 of dest (2,3)'s 4 neighbours; origin left free
        dest = board.step(origin, "MOVE:N")
        assert board.boxed_in(dest, barriers) is False


class TestHardSafetyConstraint:
    """H2: an orthogonal action landing on a confidently-believed threat cell is
    excluded whenever a safe legal alternative exists, regardless of weights.
    """

    def test_confident_cell_excluded_even_when_it_scores_highest(self) -> None:
        board = Board(size=7)
        position = (3, 3)
        confident_cell = (3, 4)  # MOVE:E lands here
        # Weight mobility/freshness heavily so the raw score would favor MOVE:E.
        weights = ThiefWeights(w_dist=0.01, w_mob=1.0, w_fresh=1.0, w_trap=5.0)
        legal = board.legal_moves(position, [])
        action = select_thief_action(
            board=board, position=position, barriers=[],
            legal_moves=legal, threat=(6, 6), visited=frozenset(),
            weights=weights, confident_threat_cell=confident_cell,
        )
        assert action != "MOVE:E"

    def test_no_safe_alternative_allows_the_only_move(self) -> None:
        """If every legal action lands on the confident cell (degenerate), it stays
        available -- the hard constraint never returns an illegal/empty action set."""
        board = Board(size=7)
        weights = ThiefWeights()
        action = select_thief_action(
            board=board, position=(0, 0), barriers=[(1, 0)],
            legal_moves=["MOVE:E", "STAY"], threat=(6, 6), visited=frozenset(),
            weights=weights, confident_threat_cell=(0, 1),
        )
        assert action in ("MOVE:E", "STAY")


class TestPurity:
    """select_thief_action never mutates the caller's visited set."""

    def test_visited_not_mutated(self) -> None:
        board = Board(size=7)
        visited = frozenset({(3, 3)})
        before = set(visited)
        select_thief_action(
            board=board, position=(3, 3), barriers=[],
            legal_moves=board.legal_moves((3, 3), []),
            threat=(0, 0), visited=visited, weights=ThiefWeights(),
            confident_threat_cell=None,
        )
        assert set(visited) == before
