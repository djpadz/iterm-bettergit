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
from iterm2.statusbar import CheckboxKnob, Knob
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
        knobs=[
            CheckboxKnob("Debug", False, "python_bettergit_debug"),
        ],
    )

    async def trigger_update(session_id: str):
        session = app.get_session_by_id(session_id)
        if not session:
            return
        cwd = await session.async_get_variable("user.python_bettergit_cwd")
        if not cwd:
            return
        git_binary = await session.async_get_variable("user.python_bettergit_git")
        poller = pollers.setdefault(
            session_id,
            GitPoller(
                git_binary=git_binary,
                session_id=session_id,
                update_trigger=trigger_update,
            ),
        )
        poller.repo_root = find_git_root(cwd)
        poller.debug_log("Git root at", poller.repo_root)
        await poller.collect()
        await session.async_set_variable(
            "user.python_bettergit_trigger", randint(0, 65536)
        )

    # noinspection PyUnusedLocal
    @StatusBarRPC
    async def python_bettergit_callback(
        *,
        knobs: list[Knob] = None,
        python_bettergit_trigger=Reference("user.python_bettergit_trigger?"),
        session_id=Reference("id"),
    ) -> [str | list[str]]:
        if python_bettergit_trigger is None or not python_bettergit_trigger:
            return ""
        poller = pollers.get(str(session_id))
        if poller:
            if "python_bettergit_debug" in knobs:
                poller.debug = bool(knobs["python_bettergit_debug"])
            r = poller.repo_status
            if r:
                return r.render()
        return ""

    await python_bettergit_component.async_register(
        connection, python_bettergit_callback
    )

    async def _update_cwd(session_id: str):
        prompt = await async_get_last_prompt(connection, session_id)
        if prompt is None:
            return
        cwd = prompt.working_directory
        if cwd is None:
            return
        session = app.get_session_by_id(session_id)
        if not session:
            return
        await session.async_set_variable("user.python_bettergit_cwd", cwd)
        await trigger_update(session_id)

    async def prompt_monitor(session_id: str):
        session: Session = app.get_session_by_id(session_id)
        if not session:
            return
        await _update_cwd(session_id)
        async with PromptMonitor(connection, session_id) as mon:
            while True:
                await mon.async_get()
                await _update_cwd(session_id)

    async def session_termination_monitor():
        async with SessionTerminationMonitor(connection) as mon:
            while True:
                session_id = await mon.async_get()
                if session_id in pollers:
                    del pollers[session_id]

    asyncio.create_task(session_termination_monitor())
    await EachSessionOnceMonitor.async_foreach_session_create_task(app, prompt_monitor)


run_forever(main)
