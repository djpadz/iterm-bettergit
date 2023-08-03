#!/usr/bin/env python3.10
from git_poller import GitPoller
from repo_status import RepoStatus
from pathlib import Path
from typing import Optional

import iterm2


def find_git_root(path: str) -> Optional[Path]:
    p = Path(path)
    while p.name:
        if (p / ".git").is_dir():
            return p
        p = p.parent
    return None


async def main(connection):
    python_bettergit_component = iterm2.StatusBarComponent(
        short_description="Python BetterGit",
        detailed_description="Show the current branch and status of the current git repository",
        exemplar=RepoStatus.exemplar(),
        update_cadence=None,
        identifier="net.padz.iterm2.python_bettergit",
        knobs=[],
    )

    # noinspection PyUnusedLocal
    @iterm2.StatusBarRPC
    async def python_bettergit_callback(
        knobs,
        python_bettergit_cwd=iterm2.Reference("user.python_bettergit_cwd?"),
        python_bettergit_random=iterm2.Reference("user.python_bettergit_random?"),
        python_bettergit_git=iterm2.Reference("user.python_bettergit_git?"),
        session_id=iterm2.Reference("id"),
    ) -> [str | list[str]]:
        session_id = str(session_id)
        if python_bettergit_git is not None:
            python_bettergit_cwd = str(python_bettergit_cwd)
        if python_bettergit_git is not None:
            python_bettergit_git = str(python_bettergit_git)
        if not python_bettergit_cwd:
            return ""
        git_root = find_git_root(python_bettergit_cwd)
        if git_root is None:
            return ""
        print(f"{session_id}: Git root at {git_root}")
        r = await GitPoller(git_root, git_binary=python_bettergit_git).collect()
        print(f"{session_id}: {r}")
        return r.render()

    await python_bettergit_component.async_register(
        connection, python_bettergit_callback
    )


iterm2.run_forever(main)
