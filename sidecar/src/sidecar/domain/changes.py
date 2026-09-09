"""What a filesystem event means for the index.

The filesystem is noisy: a save is often a write, a rename and a second write,
and an editor can touch a file five times in a second. Deciding what is worth
re-indexing is a rule, not a reaction, so it lives here and is tested without
a filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sidecar.domain.gate import is_excluded_path, screen_path


class ChangeKind(StrEnum):
    TOUCHED = "touched"
    GONE = "gone"


@dataclass(frozen=True)
class FileChange:
    """One thing that happened to one path.

    A move is two changes, the old path gone and the new one touched, because
    the index keys on path and that is exactly what a move does to it.
    """

    path: Path
    kind: ChangeKind


def worth_reacting_to(change: FileChange, size_bytes: int) -> bool:
    """Whether this change can alter what a search returns.

    A file the gate would refuse cannot change a result, so reacting to it
    costs work and buys nothing. A deletion is always worth reacting to, even
    for a path the gate refuses, because the index may hold it as a skipped
    row and the index screen would go on listing a file that is gone.

    The size is passed in rather than read, so this stays a rule about paths
    and sizes and the caller owns the one `stat` it takes to answer.
    """
    if is_excluded_path(change.path):
        return False
    if change.kind is ChangeKind.GONE:
        return True
    return screen_path(change.path, size_bytes).accepted


def collapse(changes: list[FileChange]) -> list[FileChange]:
    """One change per path, the last one winning, in the order paths were first seen.

    A save that arrives as three writes is one re-index. A file created and
    then deleted inside the same window is a deletion, which is right: the
    index never held it and forgetting an absent file is free.
    """
    latest: dict[Path, FileChange] = {}
    for change in changes:
        latest[change.path] = change
    return list(latest.values())
