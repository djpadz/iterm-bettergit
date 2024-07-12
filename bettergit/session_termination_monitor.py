from iterm2 import SessionTerminationMonitor

from .globals import connection, cwds, pollers
from .logger import logger


async def session_termination_monitor():
    async with SessionTerminationMonitor(connection) as mon:
        while True:
            session_id = await mon.async_get()
            logger.debug("%s: session terminated", session_id)
            pollers.pop(session_id, None)
            cwds.pop(session_id, None)
