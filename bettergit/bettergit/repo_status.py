import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .config import get_config
from .logger import logger

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


@dataclass(frozen=False, kw_only=True)
class RepoStatus:
    session_id: str
    fetching: bool = False
    repo_root: Optional[Path] = None
    push_count: Optional[int] = None
    pull_count: Optional[int] = None
    current_branch: Optional[str] = None
    dirty: Optional[bool] = None
    untracked: Optional[int] = None
    modified: Optional[int] = None
    staged: Optional[int] = None
    deleted: Optional[int] = None
    stashes: Optional[int] = None
    state: Optional[str] = None
    step: Optional[int] = None
    total: Optional[int] = None

    def render(self) -> str | list[str]:
        logger.debug("%s: rendering %s", self.session_id, self)
        if self.repo_root is None:
            return ""
        if self.state:
            status_line = get_config("icon_status_other") + " " + self.state
            if self.step is not None and self.total is not None:
                status_line += f" ({self.step}/{self.total})"
            return status_line
        parts: list[str] = []
        logger.debug("%s: 1", self.session_id)
        part = get_config("icon_status_fetching") if self.fetching else ""
        parts.append(part)
        logger.debug("%s: 2", self.session_id)
        part = ""
        if self.dirty:
            part += get_config("icon_status_dirty")
        elif self.push_count or self.pull_count:
            part += get_config("icon_status_push_or_pull")
        else:
            part += get_config("icon_status_clean")
        part += f" {self.current_branch}"
        logger.debug("%s: 2a", self.session_id)
        logger.debug("%s: 2a: %s %s", self.session_id, self.push_count, self.pull_count)
        if self.push_count and self.push_count > 0:
            part += " " + get_config("icon_push_count") + f" {self.push_count}"
        logger.debug("%s: 2b", self.session_id)
        if self.pull_count and self.pull_count > 0:
            part += " " + get_config("icon_pull_count") + f" {self.pull_count}"
        logger.debug("%s: 2c", self.session_id)
        parts.append(part.strip())
        logger.debug("%s: 3", self.session_id)
        part = ""
        if self.modified and self.modified > 0:
            part += " " + get_config("icon_modified_count") + f" {self.modified}"
        if self.untracked:
            part += " " + get_config("icon_untracked_count") + f" {self.untracked}"
        if self.deleted:
            part += " " + get_config("icon_deleted_count") + f" {self.deleted}"
        parts.append(part.strip())
        logger.debug("%s: 4", self.session_id)
        part = ""
        if self.staged:
            part += " " + get_config("icon_staged_count") + f" {self.staged}"
        if self.stashes:
            part += " " + get_config("icon_stashes_count") + f" {self.stashes}"
        parts.append(part.strip())
        logger.debug("%s: 5a: %s", self.session_id, parts)
        parts = [part for part in parts if part != ""]
        logger.debug("%s: 5b: %s", self.session_id, parts)
        ret = [
            " \N{LEFT VERTICAL BOX LINE} ".join(parts[0:x])
            for x in range(1, len(parts) + 1)
        ]
        logger.debug("%s: 6: %s", self.session_id, ret)
        return ret

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> Optional["RepoStatus"]:
        logger.info("from_json: %s", json_str)
        if json_str is None or not json_str.startswith("{"):
            return None
        return cls(**json.loads(json_str))

    @classmethod
    def exemplar(cls):
        return cls(
            session_id="exemplar",
            current_branch="main",
            repo_root="/path/to/repo",
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
