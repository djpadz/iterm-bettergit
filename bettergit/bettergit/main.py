import asyncio

from iterm2 import Connection, EachSessionOnceMonitor, async_get_app

from .app_globals import app_globals
from .logger import logger
from .prompt_monitor import prompt_monitor
from .sb_component import sb_component, sb_component_callback
from .session_termination_monitor import session_termination_monitor


async def main(connection: Connection):
    app_globals.connection = connection
    app_globals.app = await async_get_app(connection)
    logger.info("BetterGit started")
    logger.info("connection is %s", connection)
    logger.info("app is %s", app_globals.app)
    logger.info("Starting session termination monitor")
    asyncio.create_task(session_termination_monitor())
    logger.info("Registering status bar component")
    asyncio.create_task(sb_component.async_register(connection, sb_component_callback))
    logger.info("Registering prompt monitor")
    await EachSessionOnceMonitor.async_foreach_session_create_task(
        app_globals.app, prompt_monitor
    )
