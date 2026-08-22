"""Pure scoring core tests: mobility counting, w_trap materiality, H2 safety gate.

FR-T3, M-04 H2 (confident threat cell exclusion), scoring.py purity.
"""

from __future__ import annotations

from common.domain.board import Board
from thief_peer.strategy.scoring import ThiefWeights, orthogonal_mobility, select_thief_action


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
    """w_trap must materially influence at least one valid fixture (PRD FR-T3 formula).

    NOTE (architectural finding, reported per task instructions rather than
    silently patched): for any destination reached by a single ORTHOGONAL
    move from a legally-occupiable origin, ``Board.boxed_in(dest, barriers)``
    can never be True in a reachable game state. One of ``dest``'s four
    orthogonal neighbours is always the origin cell the mover just vacated,
    and the origin cannot itself be a barrier while an agent legally occupies
    it (a barrier landing on an occupied cell is rule 46 capture, which ends
    the sub-game before another decision is made). So `trap(dest) == 0` for
    every MOVE action in every state ``ThiefBrain`` is ever actually asked to
    score; `trap(dest)` for STAY equals the very rule-47 self-capture
    condition that would already have ended the sub-game before `decide()`
    runs. This matches the PR #34 review's finding ("over 200k states every
    firing was an already-captured state") -- the trap TERM as specified by
    PRD FR-T3 is a one-move-deep check that domain physics make structurally
    unobservable on any reachable non-terminal state; it is not a bug in
    ``select_thief_action`` (the assertions below exercise the scoring
    function directly, at the pure-math level, and confirm w_trap DOES
    change the ranking whenever `trap(dest)` is nonzero) -- it is a gap
    between the PRD's derived-design formula and the domain's own move
    physics, which conflicts with the domain and is out of this task's
    strategy/-only write scope to resolve; see the final report.
    """

    def test_trap_term_is_live_in_the_pure_scoring_math(self) -> None:
        """At the scoring-function level (no domain-reachability constraint on
        the caller's ``barriers``), a nonzero trap(dest) changes the winner."""
        board = Board(size=7)
        # Pure-math fixture: pretend a hypothetical trap destination -- not a
        # reachable GameEngine state, but valid input to demonstrate the
        # scoring math is not dead: it correctly downweights a trapped dest.
        barriers = [(1, 1), (3, 1), (2, 0), (2, 2)]  # boxes (2,1) on all 4 sides incl. "origin"
        weights = ThiefWeights(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=5.0)
        with_trap = select_thief_action(
            board=board, position=(1, 1), barriers=barriers,
            legal_moves=["MOVE:S", "MOVE:E"],
            threat=(6, 6), visited=frozenset(), weights=weights,
            confident_threat_cell=None,
        )
        zero_trap = ThiefWeights(w_dist=1.0, w_mob=0.0, w_fresh=0.0, w_trap=0.0)
        without_trap = select_thief_action(
            board=board, position=(1, 1), barriers=barriers,
            legal_moves=["MOVE:S", "MOVE:E"],
            threat=(6, 6), visited=frozenset(), weights=zero_trap,
            confident_threat_cell=None,
        )
        assert with_trap != "MOVE:S"  # trap-weighted run avoids the boxed dest
        assert without_trap == "MOVE:S"  # zero-trap run picks it purely on distance

    def test_trap_unreachable_from_a_legally_occupied_origin(self) -> None:
        """Documents the structural finding: any single-orthogonal-move destination's
        back-neighbour (the origin) is never itself a barrier in a reachable state,
        so boxed_in(dest) is always False for that destination."""
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
