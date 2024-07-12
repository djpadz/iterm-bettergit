import asyncio
from random import randint

from iterm2 import Reference, StatusBarRPC
from iterm2.statusbar import CheckboxKnob, Knob, StatusBarComponent, StringKnob

from .app_globals import APP_ID, TRIGGER_VAR, app_globals
from .config import STRING_KNOB_CONFIGS, get_config_default, set_config
from .git_poller import GitPoller
from .logger import logger
from .logger import set_debug as logger_set_debug
from .repo_status import RepoStatus
from .utils import find_git_root

sb_component = StatusBarComponent(
    short_description="Python BetterGit",
    detailed_description="Show the current branch and status of the current git repository",
    exemplar=RepoStatus.exemplar(),
    update_cadence=None,
    identifier=APP_ID,
    knobs=[
        CheckboxKnob("Debug", False, "debug"),
        *[
            StringKnob(k.name, k.placeholder or "", get_config_default(k.key), k.key)
            for k in STRING_KNOB_CONFIGS
        ],
    ],
)


@StatusBarRPC
async def sb_component_callback(
    knobs: dict[str, Knob] = None,
    trigger=Reference(f"{TRIGGER_VAR}?"),
    session_id=Reference("id"),
) -> str | list[str]:
    logger.debug("Trigger: %s", trigger)
    while app_globals.cwds.get(session_id) is None:
        await asyncio.sleep(0.1)
    if "debug" in knobs:
        logger_set_debug(knobs["debug"] == 1)
    logger.debug("%s: start", session_id)
    for k, v in knobs.items() or {}:
        set_config(k, v)
    session_id = str(session_id)
    logger.debug("session_id is %s", session_id)
    cwd = app_globals.cwds.get(session_id)
    cwd = str(cwd)
    if session_id not in app_globals.pollers:
        logger.debug("Creating new poller for session ID %s", session_id)
        app_globals.pollers[session_id] = GitPoller(
            session_id=str(session_id),
            update_trigger=lambda _session_id: app_globals.app.async_set_variable(
                TRIGGER_VAR, randint(0, 1000000)
            ),
        )
    poller = app_globals.pollers[session_id]
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
