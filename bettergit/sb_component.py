from random import randint

from iterm2 import Reference, StatusBarRPC
from iterm2.statusbar import CheckboxKnob, Knob, StatusBarComponent, StringKnob

from .config import STRING_KNOB_CONFIGS, get_config_default, set_config
from .git_poller import GitPoller
from .globals import APP_ID, TRIGGER_VAR, app, cwds, pollers
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
):
    logger.debug("Trigger: %s", trigger)
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
        logger.debug("Creating new poller for session ID %s", session_id)
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
