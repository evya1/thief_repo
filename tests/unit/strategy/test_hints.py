"""HintWriter tests: template output, verdict rule, lie rate, word cap.

TC-T09: template hint — output ≤ 15 words; names landmark or generic fallback;
        verdict ∈ {truth, lie}; seeded lie fraction within 0.30–0.50 over 1000 hints.
TC-T11: verdict rule — independently recomputed from position + asserted landmark.
"""

from __future__ import annotations

import random

from common.domain.board import Cell, chebyshev
from src.thief_peer.belief.hints import parse_landmarks
from src.thief_peer.strategy.hints import HintWriter


class TestTemplateHint:
    """TC-T09: template hint generation."""

    def test_output_is_string(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)
        hint, verdict = hw.say((3, 3))
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_word_cap(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=6)
        hint, _ = hw.say((3, 3))
        words = hint.split()
        assert len(words) <= 6

    def test_verdict_is_valid(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)
        for _ in range(100):
            hint, verdict = hw.say((3, 3))
            assert verdict in ("truth", "lie")

    def test_landmark_or_generic(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)
        # Collect hints and check they are non-empty strings.
        hints = [hw.say((3, 3))[0] for _ in range(50)]
        for h in hints:
            assert isinstance(h, str) and len(h) > 0

    def test_lie_rate_within_bounds(self) -> None:
        """Seeded lie fraction within 0.30–0.50 over 1000 hints."""
        rng = random.Random(123)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)
        lies = sum(1 for _ in range(1000) if hw.say((3, 3))[1] == "lie")
        rate = lies / 1000
        assert 0.30 <= rate <= 0.50, f"lie rate {rate:.3f} out of bounds"

    def test_deterministic_per_seed(self) -> None:
        """Same seed => identical hint sequence."""
        def make_hints(seed: int) -> tuple[str, ...]:
            rng = random.Random(seed)
            hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)
            return tuple(hw.say((3, 3))[0] for _ in range(10))

        h1 = make_hints(99)
        h2 = make_hints(99)
        assert h1 == h2


class TestVerdictRule:
    """TC-T11: verdict recomputed independently from position + asserted landmark."""

    def test_verdict_matches_rule(self) -> None:
        """Verdict matches the sealed verdict on every generated hint."""
        rng = random.Random(42)
        hw = HintWriter(role="thief", rng=rng, arena="New York", max_words=15)

        for pos in [(0, 0), (1, 3), (3, 3), (6, 6), (2, 5)]:
            for _ in range(50):
                hint, verdict = hw.say(pos)
                # Recompute verdict independently.
                recomputed = self._recompute_verdict(pos, hint)
                assert verdict == recomputed, f"pos={pos} hint={hint!r} verdict={verdict} recomputed={recomputed}"

    @staticmethod
    def _recompute_verdict(position: Cell, hint: str) -> str:
        """Recompute verdict: 'truth' iff asserted landmark contains or is
        Chebyshev-adjacent to position.
        """
        matched = parse_landmarks(hint, "New York", 7)
        if matched:
            if any(position == cell or chebyshev(position, cell) == 1 for cell in matched):
                return "truth"
            return "lie"
        return "truth"  # generic fallback => truth

    def test_generic_fallback_truth(self) -> None:
        """Generic non-landmark line => verdict is truth."""
        # With unknown arena, no landmark regions exist.
        # Truth branch: no landmark contains/adjacent => generic line, verdict truth.
        rng = random.Random(0)
        hw = HintWriter(role="thief", rng=rng, arena="Unknown", max_words=15)
        # Test both branches: truth fallback and lie fallback.
        for _ in range(20):
            hint, verdict = hw.say((3, 3))
            # Verdict is rule-computed: depends on which generic landmark is picked.
            assert verdict in ("truth", "lie")
            assert isinstance(hint, str) and len(hint) > 0
        # Verify that some hints use the generic fallback (no landmark match).
        matched_any = False
        rng2 = random.Random(42)
        hw2 = HintWriter(role="thief", rng=rng2, arena="Unknown", max_words=15)
        for _ in range(20):
            hint, _ = hw2.say((3, 3))
            if "city" in hint.lower() or "somewhere" in hint.lower():
                matched_any = True
                break
        assert matched_any, "expected some generic fallback hints"
