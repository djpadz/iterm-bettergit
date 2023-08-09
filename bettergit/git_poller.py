import aiofiles
import asyncio
import shutil
from asyncio import Future
from pathlib import Path
from repo_status import RepoStatus
from typing import Optional

POLLING_INTERVAL = 5 * 60  # 5 minutes

last_poll: dict[Path, int] = {}


class GitPoller:
    def __init__(
        self,
        repo_root: str | Path,
        git_binary: Optional[str | Path] = None,
    ):
        self.repo_root = repo_root
        self.git_binary = git_binary or shutil.which("git")
        self.collection_methods = [
            getattr(self, x) for x in dir(self) if x.startswith("collect_")
        ]
        self.fetch_future: Optional[Future] = None

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @repo_root.setter
    def repo_root(self, value: str | Path):
        self._repo_root = Path(value)

    @property
    def git_binary(self) -> Path:
        return self._git_binary

    @git_binary.setter
    def git_binary(self, value: str | Path):
        self._git_binary = Path(value)

    async def collect(self) -> RepoStatus:
        if self.fetch_future is not None:
            if self.fetch_future.done():
                await self.fetch_future
                self.fetch_future = None
                print(f"Done fetching {self.repo_root}")
        else:
            if (
                last_poll.setdefault(self.repo_root, 0) + POLLING_INTERVAL
                < asyncio.get_event_loop().time()
            ):
                print(f"Fetching {self.repo_root}")
                self.fetch_future = asyncio.create_task(
                    self._run_git_command("fetch", "--quiet")
                )
                last_poll[self.repo_root] = asyncio.get_event_loop().time()
        futures = [asyncio.create_task(x()) for x in self.collection_methods]
        results = await asyncio.gather(*futures)
        res = {}
        for r in results:
            res.update(r)
        # noinspection PyArgumentList
        return RepoStatus(**res)

    @staticmethod
    async def _run_command(command: str, /, *args, cwd: Path) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode()

    @staticmethod
    async def _read_first_line_int(f: [Path | str]) -> int:
        async with aiofiles.open(f, mode="r") as f:
            async for line in f:
                return int(line.strip())

    async def _run_git_command(self, /, *args, cwd: Path = None) -> tuple[str, int]:
        if cwd is None:
            cwd = self.repo_root
        return await self._run_command(self.git_binary, *args, cwd=cwd)

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
