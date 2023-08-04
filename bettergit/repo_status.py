from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, kw_only=True)
class RepoStatus:
    push_count: int
    pull_count: int
    current_branch: str
    dirty: bool
    untracked: int
    modified: int
    staged: int
    deleted: int
    stashes: int
    state: Optional[str]
    step: Optional[int]
    total: Optional[int]

    def render(self) -> [str | list[str]]:
        if self.state:
            status_line = f"\u203C\uFE0F {self.state}"  # Red double exclamation mark
            if self.step is not None and self.total is not None:
                status_line += f" ({self.step}/{self.total})"
            return status_line
        parts: list[str] = []
        part = ""
        if self.dirty:
            part += "\U0001F534"  # Red circle
        elif self.push_count or self.pull_count:
            part += "\U0001F7E1"  # Yellow circle
        else:
            part += "\U0001F7E2"  # Green circle
        part += f" {self.current_branch}"
        if self.push_count > 0:
            part += f" \N{UPWARDS BLACK ARROW} {self.push_count}"
        if self.pull_count > 0:
            part += f" \N{DOWNWARDS BLACK ARROW} {self.pull_count}"
        parts.append(part.strip())
        part = ""
        if self.modified > 0:
            part += f" \N{LOWER RIGHT PENCIL} {self.modified}"
        if self.untracked:
            part += f" \N{WARNING SIGN} {self.untracked}"
        if self.deleted:
            part += f" \N{MINUS SIGN} {self.deleted}"
        parts.append(part.strip())
        part = ""
        if self.staged:
            part += f" \N{CHECK MARK} {self.staged}"
        if self.stashes:
            part += f" \N{UP ARROWHEAD IN A RECTANGLE BOX} {self.stashes}"
        parts.append(part.strip())
        parts = [part for part in parts if part != ""]
        return [
            " \N{LEFT VERTICAL BOX LINE} ".join(parts[0:x])
            for x in range(1, len(parts) + 1)
        ]

    @classmethod
    def exemplar(cls):
        return cls(
            current_branch="main",
            dirty=True,
            push_count=2,
            pull_count=5,
            modified=3,
            untracked=2,
            deleted=4,
            staged=10,
            stashes=3,
            state=None,
            step=None,
            total=None,
        ).render()[-1]
