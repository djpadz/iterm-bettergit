#!/usr/bin/env python3.10
import asyncio
from config import STRING_KNOB_CONFIGS, get_config_default, set_config
from git_poller import GitPoller
from iterm2 import (
    App,
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

TRIGGER_VAR = "user.python_bettergit_trigger"
CWD_VAR = "user.python_bettergit_cwd"


def find_git_root(path: str) -> Optional[Path]:
    p = Path(path)
    while p.name:
        if (p / ".git").is_dir():
            return p
        p = p.parent
    return None


async def main(connection):
    pollers: dict[str, GitPoller] = {}
    cwds: dict[str, str] = {}

    logger.debug("start")
    app: App = await async_get_app(connection)
    logger.debug("Got app")

    @StatusBarRPC
    async def sb_component_callback(
        knobs: dict[str, Knob] = None,
        _trigger=Reference(f"{TRIGGER_VAR}?"),
        session_id=Reference("id"),
    ):
        if "debug" in knobs:
            logger_set_debug(knobs["debug"] == 1)
        logger.debug("%s: start", session_id)
        for k, v in knobs.items() or {}:
            set_config(k, v)
        session_id = str(session_id)
        cwd = cwds.get(session_id)
        if cwd is None:
            logger.debug("%s: no cwd", session_id)
            return ""
        cwd = str(cwd)
        if session_id not in pollers:
            pollers[session_id] = GitPoller(
                session_id=str(session_id),
                update_trigger=lambda _session_id: app.async_set_variable(
                    TRIGGER_VAR, randint(0, 1000000)
                ),
            )
        poller = pollers[session_id]
        poller.repo_root = find_git_root(cwd)
        logger.debug("%s: Git root at %s", session_id, poller.repo_root)
        await poller.collect()
        logger.debug("%s: Repo status: %s", session_id, poller.repo_status)
        if poller is None:
            logger.debug("%s: no poller", session_id)
            return ""
        r = poller.repo_status
        logger.debug("%s: repo status: %s", session_id, r)
        ret = r.render() if r else ""
        logger.debug('%s: returning "%s"', session_id, ret)
        return ret

    async def _update_cwd(session_id: str) -> bool:
        prompt = await async_get_last_prompt(connection, session_id)
        if prompt is None:
            return
        cwd = prompt.working_directory
        if cwd is None:
            return
        session = app.get_session_by_id(session_id)
        if session:
            cwds[session_id] = cwd
            await session.async_set_variable(TRIGGER_VAR, randint(0, 1000000))
            return True
        logger.debug("%s: Session not found", session_id)
        pollers.pop(session_id, None)
        cwds.pop(session_id, None)
        return False

    async def prompt_monitor(session_id: str):
        session: Session = app.get_session_by_id(session_id)
        if not session:
            return
        await _update_cwd(session_id)
        async with PromptMonitor(connection, session_id) as mon:
            while True:
                await mon.async_get()
                if not await _update_cwd(session_id):
                    break
        logger.debug("%s: prompt monitor done", session_id)

    async def session_termination_monitor():
        async with SessionTerminationMonitor(connection) as mon:
            while True:
                session_id = await mon.async_get()
                logger.debug("%s: session terminated", session_id)
                pollers.pop(session_id, None)
                cwds.pop(session_id, None)

    sb_component = StatusBarComponent(
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

    await sb_component.async_register(connection, sb_component_callback)
    asyncio.create_task(session_termination_monitor())
    await EachSessionOnceMonitor.async_foreach_session_create_task(app, prompt_monitor)


logger.debug("running forever!")
run_forever(main)
