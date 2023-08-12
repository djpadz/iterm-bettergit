from dataclasses import dataclass
from typing import Optional
from config import get_config

LICENSE = """
Copyright 2023 Dj Padzensky

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
"""


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
