from iterm2 import SessionTerminationMonitor

from .app_globals import app_globals
from .logger import logger


async def session_termination_monitor():
    async with SessionTerminationMonitor(app_globals.connection) as mon:
        while True:
            session_id = await mon.async_get()
            logger.debug("%s: session terminated", session_id)
            app_globals.pollers.pop(session_id, None)
            app_globals.cwds.pop(session_id, None)
