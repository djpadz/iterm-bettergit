#!/usr/bin/env python3.10
import asyncio
from git_poller import GitPoller
from iterm2 import (
    EachSessionOnceMonitor,
    PromptMonitor,
    Reference,
    Session,
    SessionTerminationMonitor,
    StatusBarComponent,
    StatusBarRPC,
    async_get_app,
    async_get_last_prompt,
    run_forever,
)
from iterm2.statusbar import Knob
from pathlib import Path
from random import randint
from repo_status import RepoStatus
from typing import Optional

pollers: dict[str, GitPoller] = {}


def find_git_root(path: str) -> Optional[Path]:
    p = Path(path)
    while p.name:
        if (p / ".git").is_dir():
            return p
        p = p.parent
    return None


async def main(connection):
    app = await async_get_app(connection)

    python_bettergit_component = StatusBarComponent(
        short_description="Python BetterGit",
        detailed_description="Show the current branch and status of the current git repository",
        exemplar=RepoStatus.exemplar(),
        update_cadence=None,
        identifier="net.padz.iterm2.python_bettergit",
        knobs=[],
    )

    # noinspection PyUnusedLocal
    @StatusBarRPC
    async def python_bettergit_callback(
        *,
        knobs: list[Knob] = None,
        python_bettergit_cwd=Reference("user.python_bettergit_cwd?"),
        python_bettergit_git=Reference("user.python_bettergit_git?"),
        session_id=Reference("id"),
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
        poller = pollers.setdefault(
            session_id,
            GitPoller(
                git_binary=python_bettergit_git,
                session=app.get_session_by_id(session_id),
            ),
        )
        poller.repo_root = git_root
        await poller.debug_log("Git root at ", git_root)
        r = await poller.collect()
        return r.render()

    await python_bettergit_component.async_register(
        connection, python_bettergit_callback
    )

    async def prompt_monitor(session_id):
        session: Session = app.get_session_by_id(session_id)
        if not session:
            return
        async with PromptMonitor(connection, session_id) as mon:
            while True:
                _mode, prompt = await mon.async_get()
                if prompt is None:
                    prompt = await async_get_last_prompt(connection, session_id)
                if prompt is None:
                    continue
                cwd = prompt.working_directory
                if cwd is None:
                    continue
                # Prefix the value with a random number to force the status bar to update.
                await session.async_set_variable(
                    "user.python_bettergit_cwd", f"{randint(0,65536)} {cwd}"
                )

    async def session_termination_monitor():
        async with SessionTerminationMonitor(connection) as mon:
            while True:
                session_id = await mon.async_get()
                print(f"{session_id}: Terminated")
                if session_id in pollers:
                    del pollers[session_id]

    asyncio.create_task(session_termination_monitor())
    await EachSessionOnceMonitor.async_foreach_session_create_task(app, prompt_monitor)


run_forever(main)
