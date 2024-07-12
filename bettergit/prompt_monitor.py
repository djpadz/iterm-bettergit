from random import randint

from iterm2 import PromptMonitor, Session, async_get_last_prompt

from .globals import TRIGGER_VAR, app, connection, cwds, pollers
from .logger import logger


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
