"""Which of the user's folders a path belongs to, and whether it may be searched.

Two features ask the same question. The watcher asks it to give a changed file
the right folder id, and search asks it to leave out a folder the user turned
off. Answering it twice in two places is how the two would come to disagree.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sidecar.domain.entities import Folder


def folder_holding(path: Path, folders: Sequence[Folder]) -> Folder | None:
    """The innermost folder this path is under, `None` when no folder is.

    Innermost rather than first, because a user who indexed both a folder and
    a folder inside it means the file to belong to the one they named last.
    """
    holding = [folder for folder in folders if path.is_relative_to(folder.path)]
    return max(holding, key=lambda folder: len(folder.path.parts), default=None)


def is_searchable(path: Path, folders: Sequence[Folder]) -> bool:
    """False only for a path inside a folder the user turned off.

    A path under no folder at all stays searchable. Removing a folder leaves
    its files in the index on purpose, for the user who is moving a folder
    rather than disowning it, and those files must not silently stop being
    findable because the row that named their folder is gone.
    """
    holding = folder_holding(path, folders)
    return holding is None or holding.enabled
