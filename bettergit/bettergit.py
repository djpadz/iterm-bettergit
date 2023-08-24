#!/usr/bin/env python3.10
import asyncio
from config import STRING_KNOB_CONFIGS, get_config_default, set_config
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
from iterm2.statusbar import CheckboxKnob, Knob, StringKnob
from logger import logger, set_debug as logger_set_debug
from pathlib import Path
from random import randint
from repo_status import RepoStatus
from typing import Optional

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
            CheckboxKnob("Debug", False, "debug"),
            *[
                StringKnob(
                    k.name, k.placeholder or "", get_config_default(k.key), k.key
                )
                for k in STRING_KNOB_CONFIGS
            ],
        ],
    )

    async def trigger_update(session_id: str):
        session = app.get_session_by_id(session_id)
        if not session:
            return
        cwd = await session.async_get_variable("user.python_bettergit_cwd")
        if not cwd:
            return
        poller = pollers.setdefault(
            session_id,
            GitPoller(
                session_id=session_id,
                update_trigger=trigger_update,
            ),
        )
        poller.repo_root = find_git_root(cwd)
        logger.debug("%s: Git root at %s", session_id, poller.repo_root)
        await poller.collect()
        await session.async_set_variable(
            "user.python_bettergit_trigger", randint(0, 65536)
        )

    # noinspection PyUnusedLocal
    @StatusBarRPC
    async def python_bettergit_callback(
        knobs: dict[str, Knob] = None,
        python_bettergit_trigger=Reference("user.python_bettergit_trigger?"),
        session_id=Reference("id"),
    ) -> [str | list[str]]:
        poller = pollers.get(str(session_id))
        if poller is None:
            return ""
        if knobs is not None:
            for k, v in knobs.items():
                set_config(k, v)
                if k == "debug":
                    logger_set_debug(v)
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
    asyncio.create_task(
        EachSessionOnceMonitor.async_foreach_session_create_task(app, prompt_monitor)
    )


run_forever(main)
