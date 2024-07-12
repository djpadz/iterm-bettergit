from random import randint

from iterm2 import PromptMonitor, Session, async_get_last_prompt

from .app_globals import TRIGGER_VAR, app_globals
from .logger import logger


async def _update_cwd(session_id: str) -> bool:
    prompt = await async_get_last_prompt(app_globals.connection, session_id)
    logger.debug("prompt is %s", prompt)
    if prompt is None:
        return
    cwd = prompt.working_directory
    logger.debug("cwd is %s", cwd)
    if cwd is None:
        return
    session = app_globals.app.get_session_by_id(session_id)
    logger.debug("session is %s", session)
    logger.debug("session_id is %s", session_id)
    if session:
        app_globals.cwds[session_id] = cwd
        logger.debug("%s: cwd updated to %s", session_id, cwd)
        await session.async_set_variable(TRIGGER_VAR, randint(0, 1000000))
        return True
    logger.debug("%s: Session not found", session_id)
    app_globals.pollers.pop(session_id, None)
    app_globals.cwds.pop(session_id, None)
    return False


async def prompt_monitor(session_id: str):
    session: Session = app_globals.app.get_session_by_id(session_id)
    if not session:
        return
    await _update_cwd(session_id)
    async with PromptMonitor(app_globals.connection, session_id) as mon:
        while True:
            await mon.async_get()
            if not await _update_cwd(session_id):
                break
    logger.debug("%s: prompt monitor done", session_id)
