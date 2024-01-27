import aiofiles
import asyncio
import os
import shutil
from asyncio import Future
from config import get_config
from logger import logger
from pathlib import Path
from repo_status import RepoStatus
from typing import Awaitable, Callable, Optional

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

    async def _do_fetch(self) -> None:
        cur_root = self.repo_root
        logger.debug("%s: Fetching in %s", self.session_id, cur_root)
        await self._run_git_command("fetch", "--quiet")
        last_poll[cur_root] = asyncio.get_event_loop().time()
        logger.debug("%s: Done fetching in %s", self.session_id, cur_root)
        if self.repo_root == cur_root and self.update_trigger:
            await self.update_trigger(self.session_id)

    async def collect(self) -> None:
        if self.repo_root is None:
            self.repo_status = None
            return
        if self.fetch_future is not None:
            if self.fetch_future.done():
                logger.debug(
                    "%s: Reaping future %s", self.session_id, self.fetch_future
                )
                await self.fetch_future
                self.fetch_future = None
                last_poll[self.repo_root] = asyncio.get_event_loop().time()
        else:
            rc, stdout = await self._run_git_command("remote", "show")
            if stdout.strip() and (
                last_poll.setdefault(self.repo_root, 0) + POLLING_INTERVAL
                < asyncio.get_event_loop().time()
            ):
                if self.fetch_future is None:
                    self.fetch_future = asyncio.create_task(self._do_fetch())
                    logger.debug("%s: created: %s", self.session_id, self.fetch_future)
        results = await asyncio.gather(
            *[asyncio.create_task(x()) for x in self.collection_methods]
        )
        res = {"session_id": self.session_id}
        for r in results:
            res.update(r)
        # noinspection PyArgumentList
        self.repo_status = RepoStatus(**res)

    async def _run_command(
        self, command: [str | Path], /, *args, cwd: Path
    ) -> tuple[int, str]:
        logger.debug("%s: Running %s %s in %s", self.session_id, command, args, cwd)
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        logger.debug("%s: Done running %s %s", self.session_id, command, args)
        logger.debug("%s: rc: %d", self.session_id, proc.returncode)
        logger.debug("%s: stdout: %s", self.session_id, stdout)
        logger.debug("%s: stderr: %s", self.session_id, stderr)
        return proc.returncode, stdout.decode()

    async def _run_git_command(self, /, *args, cwd: Path = None) -> tuple[int, str]:
        if cwd is None:
            cwd = self.repo_root
        git_binary = get_config("git_binary")
        if not Path(git_binary).is_file() and shutil.which(git_binary) is None:
            raise Exception(f"git binary {git_binary} not found")
        cur_path = os.getenv("PATH", os.path.defpath)
        try:
            if Path(git_binary).is_absolute():
                new_path = cur_path.split(os.path.pathsep)
                new_path.append(str(Path(git_binary).parent))
                os.environ["PATH"] = os.path.pathsep.join(new_path)
            return await self._run_command(get_config("git_binary"), *args, cwd=cwd)
        finally:
            os.environ["PATH"] = cur_path

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
