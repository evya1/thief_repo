"""Strategy package — shared core + Thief-specific policy.

Public re-exports. The shared-core files are identical in both role
repositories modulo package import path and the role constant.
"""

from __future__ import annotations

from .base import BrainBase
from .baseline import BaselineStrategy, Strategy
from .decision import Decision
from .hints import HintWriter, TextProvider
from .inject import resolve_brain, resolve_brain_cls
from .thief import ThiefBrain

__all__ = [
    "BaselineStrategy",
    "BrainBase",
    "Decision",
    "HintWriter",
    "Strategy",
    "TextProvider",
    "ThiefBrain",
    "resolve_brain",
    "resolve_brain_cls",
]
