import json

from iterm2 import Reference, StatusBarRPC
from iterm2.statusbar import CheckboxKnob, Knob, StatusBarComponent, StringKnob

from .app_globals import APP_ID
from .config import STRING_KNOB_CONFIGS, get_config_default, set_config
from .logger import logger
from .logger import set_debug as logger_set_debug
from .repo_status import RepoStatus

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
    trigger=Reference("user.python_bettergit_trigger?"),
    session_id=Reference("id"),
) -> str | list[str]:
    logger.debug("%s: SB Wake up!", str(session_id))
    if "debug" in knobs:
        logger_set_debug(knobs["debug"] == 1)
    for k, v in knobs.items() or {}:
        set_config(k, v)
    logger.debug("%s: got %s", session_id, trigger)
    if not trigger or not str(trigger).startswith("["):
        return ""
    trigger_val = json.loads(str(trigger))
    logger.debug("%s: returning %s", session_id, trigger_val)
    return trigger_val
