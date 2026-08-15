"""One peer's own half of a sub-game — local truth only.

The book's model is hidden positions: each peer knows where **it** is and never where the rival
is (book ch.1, ch.5; App. E rules 8-9 forbid even *displaying* the objective board). So there is
no referee object here and no shared board state. What exists is:

* your own position, which only you know;
* the barriers, which are public because the cop must declare every placement truthfully
  (App. E rules 15-16) — lying about one is grounds for disqualification;
* the rival's transmitted scent field, which cannot lie: it is emitted by movement itself.

That shape makes adjudication **distributed**, and it is the part most worth understanding before
you build your own peer:

* the cop cannot know it has captured anyone. It issues a ``capture_claim`` at a cell and the
  thief answers. App. E rule 21 makes that answer a cryptographic obligation — a lie is provable
  at the audit against the sealed ``state`` string, so the thief's honest answer is the cheapest
  move available to it as well as the required one;
* a barrier dropped on the thief's own cell is a capture (rule 46) that the **thief** notices;
* a thief with no legal move is captured (rule 47), which again only the thief can see;
* survival at the threshold is claimed by the thief.

So this engine never decides the game from a position it should not have. It decides only what it
is entitled to know.
"""

from common.domain.rules import GameEngine, IllegalMoveError

__all__ = [
    "GameEngine",
    "IllegalMoveError",
]
