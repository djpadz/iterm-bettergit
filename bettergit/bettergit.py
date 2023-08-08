#!/usr/bin/env python3.10
import iterm2
from git_poller import GitPoller
from pathlib import Path
from random import randint
from repo_status import RepoStatus
from typing import Optional


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
        *,
        knobs: list[iterm2.statusbar.Knob] = None,
        python_bettergit_cwd=iterm2.Reference("user.python_bettergit_cwd?"),
        python_bettergit_git=iterm2.Reference("user.python_bettergit_git?"),
        session_id=iterm2.Reference("id"),
    ) -> [str | list[str]]:
        session_id = str(session_id)
        if python_bettergit_cwd is None:
            return ""
        python_bettergit_git = (
            None if python_bettergit_git is None else str(python_bettergit_git)
        )
        python_bettergit_cwd = str(python_bettergit_cwd).split(maxsplit=1)[1]
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

    app = await iterm2.async_get_app(connection)

    async def monitor(session_id):
        session: iterm2.Session = app.get_session_by_id(session_id)
        if not session:
            return
        async with iterm2.PromptMonitor(connection, session_id) as mon:
            while True:
                _mode, prompt = await mon.async_get()
                if prompt is None:
                    prompt = await iterm2.async_get_last_prompt(connection, session_id)
                if prompt is None:
                    continue
                cwd = prompt.working_directory
                if cwd is None:
                    continue
                # Prefix the value with a random number to force the status bar to update.
                await session.async_set_variable(
                    "user.python_bettergit_cwd", f"{randint(0,65536)} {cwd}"
                )

    await iterm2.EachSessionOnceMonitor.async_foreach_session_create_task(app, monitor)


iterm2.run_forever(main)
