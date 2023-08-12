import asyncio
import shutil
from asyncio import Future
from pathlib import Path
from typing import Awaitable, Callable, Optional

import aiofiles

from config import get_config
from repo_status import RepoStatus

"""
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

POLLING_INTERVAL = 10  # 5 minutes

last_poll: dict[Path, float] = {}


class GitPoller:
    def __init__(
        self,
        session_id: str,
        update_trigger: Optional[Callable[[str], Awaitable[any]]] = None,
    ):
        self.repo_root = None
        self.session_id = session_id
        self.update_trigger = update_trigger
        self.git_binary = get_config("git_binary") or shutil.which("git")
        self.repo_status = None
        self.collection_methods = [
            getattr(self, x) for x in dir(self) if x.startswith("collect_")
        ]
        self.fetch_future: Optional[Future] = None

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @repo_root.setter
    def repo_root(self, value: str | Path):
        self._repo_root = Path(value) if value else None

    @property
    def git_binary(self) -> Path:
        return self._git_binary

    @git_binary.setter
    def git_binary(self, value: str | Path):
        self._git_binary = Path(value)

    def debug_log(self, *args) -> None:
        if get_config("debug"):
            print(f"{self.session_id}:", *args)

    async def _do_fetch(self) -> None:
        cur_root = self.repo_root
        self.debug_log("Fetching in", cur_root)
        await self._run_git_command("fetch", "--quiet")
        last_poll[cur_root] = asyncio.get_event_loop().time()
        self.debug_log("Done fetching in", cur_root)
        if self.repo_root == cur_root:
            if self.update_trigger:
                await self.update_trigger(self.session_id)

    async def collect(self) -> None:
        if self.repo_root is None:
            self.repo_status = None
            return
        if self.fetch_future is not None:
            if self.fetch_future.done():
                self.debug_log("Reaping future", self.fetch_future)
                await self.fetch_future
                self.fetch_future = None
                last_poll[self.repo_root] = asyncio.get_event_loop().time()
        else:
            rc, stdout = await self._run_git_command("remote", "show")
            if stdout.strip() and (
                last_poll.setdefault(self.repo_root, 0) + POLLING_INTERVAL
                < asyncio.get_event_loop().time()
            ):
                self.fetch_future = asyncio.create_task(self._do_fetch())
                self.debug_log("created:", self.fetch_future)
        futures = [asyncio.create_task(x()) for x in self.collection_methods]
        results = await asyncio.gather(*futures)
        res = {}
        for r in results:
            res.update(r)
        # noinspection PyArgumentList
        self.repo_status = RepoStatus(**res)

    async def _run_command(
        self, command: [str | Path], /, *args, cwd: Path
    ) -> tuple[int, str]:
        self.debug_log("Running ", command, *args, "in", cwd)
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        self.debug_log("Done running ", command)
        self.debug_log("rc:", proc.returncode)
        self.debug_log("stdout:", stdout)
        self.debug_log("stderr:", stderr)
        return proc.returncode, stdout.decode()

    async def _run_git_command(self, /, *args, cwd: Path = None) -> tuple[int, str]:
        if cwd is None:
            cwd = self.repo_root
        return await self._run_command(self.git_binary, *args, cwd=cwd)

    @staticmethod
    async def _read_first_line_int(f: [Path | str]) -> int:
        async with aiofiles.open(f, mode="r") as f:
            return int((await f.readline()).strip())

    async def collect_repo_counts(self) -> dict[str, int]:
        rc, stdout = await self._run_git_command(
            "status", "--porcelain", "--ignore-submodules", "-unormal"
        )
        if rc != 0:
            raise Exception(f"git status failed: {stdout}")
        dirty = False
        untracked = 0
        modified = 0
        staged = 0
        deleted = 0
        for line in stdout.splitlines():
            dirty = True
            status = line[0:2]
            if status == "??":
                untracked += 1
            elif status == "AM":
                staged += 1
                modified += 1
            elif status == " M":
                modified += 1
            elif status == " D":
                deleted += 1
            elif status[0] == "A":
                staged += 1
            elif status[0] == "M":
                staged += 1
            elif status[0] == "D":
                staged += 1
        return {
            "dirty": dirty,
            "untracked": untracked,
            "modified": modified,
            "staged": staged,
            "deleted": deleted,
        }

    async def collect_current_branch(self) -> dict[str, str]:
        rc, stdout = await self._run_git_command("branch", "--show-current")
        if rc == 0 and stdout != "":
            return {"current_branch": stdout.strip()}
        rc, stdout = await self._run_git_command("rev-parse", "--short", "HEAD")
        if rc == 0:
            return {"current_branch": f"[{stdout.strip()}]"}  # detached HEAD
        raise Exception(f"git branch failed: {stdout}")

    async def collect_stashes(self) -> dict[str, int]:
        rc, stdout = await self._run_git_command("stash", "list")
        if rc != 0:
            raise Exception(f"git stash failed: {stdout}")
        return {"stashes": len(stdout.splitlines())}

    async def collect_counts(self) -> dict[str, int]:
        rc, stdout = await self._run_git_command(
            "rev-list", "--left-right", "--count", "HEAD...@{u}"
        )
        if rc == 0:
            push_count, pull_count = map(int, stdout.split())
        else:
            push_count, pull_count = 0, 0
        return {"push_count": push_count, "pull_count": pull_count}

    async def collect_repo_state(self) -> dict[str, int | str]:
        git_dir = self.repo_root / ".git"
        rebase_dir = git_dir / "rebase-merge"
        state = None
        step = None
        total = None
        if rebase_dir.is_dir():
            state = f"REBASE-{'i' if (rebase_dir / 'interactive').exists() else 'm'}"
            step = await self._read_first_line_int(rebase_dir / "msgnum")
            total = await self._read_first_line_int(rebase_dir / "end")
        else:
            rebase_dir = git_dir / "rebase-apply"
            if rebase_dir.is_dir():
                step = await self._read_first_line_int(rebase_dir / "next")
                total = await self._read_first_line_int(rebase_dir / "last")
                if (rebase_dir / "rebasing").exists():
                    state = "REBASE"
                elif (rebase_dir / "applying").exists():
                    state = "AM"
                else:
                    state = "AM/REBASE"
            elif (git_dir / "MERGE_HEAD").exists():
                state = "MERGING"
            elif (git_dir / "CHERRY_PICK_HEAD").exists():
                state = "CHERRY-PICKING"
            elif (git_dir / "REVERT_HEAD").exists():
                state = "REVERTING"
            elif (git_dir / "BISECT_LOG").exists():
                state = "BISECTING"
        return {"state": state, "step": step, "total": total}
