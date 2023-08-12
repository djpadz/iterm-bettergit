from dataclasses import dataclass
from typing import Optional
from config import get_config


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
            status_line = get_config("icon_status_other") + " " + self.state
            if self.step is not None and self.total is not None:
                status_line += f" ({self.step}/{self.total})"
            return status_line
        parts: list[str] = []
        part = ""
        if self.dirty:
            part += get_config("icon_status_dirty")
        elif self.push_count or self.pull_count:
            part += get_config("icon_status_push_or_pull")
        else:
            part += get_config("icon_status_clean")
        part += f" {self.current_branch}"
        if self.push_count > 0:
            part += " " + get_config("icon_push_count") + f" {self.push_count}"
        if self.pull_count > 0:
            part += " " + get_config("icon_pull_count") + f" {self.pull_count}"
        parts.append(part.strip())
        part = ""
        if self.modified > 0:
            part += " " + get_config("icon_modified_count") + f" {self.modified}"
        if self.untracked:
            part += " " + get_config("icon_untracked_count") + f" {self.untracked}"
        if self.deleted:
            part += " " + get_config("icon_deleted_count") + f" {self.deleted}"
        parts.append(part.strip())
        part = ""
        if self.staged:
            part += " " + get_config("icon_staged_count") + f" {self.staged}"
        if self.stashes:
            part += " " + get_config("icon_stashes_count") + f" {self.stashes}"
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
