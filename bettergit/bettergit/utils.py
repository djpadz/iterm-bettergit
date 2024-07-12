from os import PathLike
from pathlib import Path
from typing import Optional


def find_git_root(path: PathLike | str) -> Optional[Path]:
    p = Path(path)
    while p.name:
        if (p / ".git").is_dir():
            return p
        p = p.parent
    return None
