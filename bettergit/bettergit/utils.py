from os import PathLike
from pathlib import Path
from typing import Optional


def find_git_root(path: PathLike | str) -> Optional[Path]:
    p = Path(path)
    while True:
        if (p / ".git").is_dir():
            return p
        if not p.name:
            break
        p = p.parent
    return None
