import asyncio

from iterm2 import Connection, EachSessionOnceMonitor, async_get_app, run_forever

from .globals import app, set_app, set_connection
from .logger import logger
from .prompt_monitor import prompt_monitor
from .sb_component import sb_component, sb_component_callback
from .session_termination_monitor import session_termination_monitor


async def main(connection: Connection):
    set_connection(connection)
    set_app(await async_get_app(connection))

    await sb_component.async_register(connection, sb_component_callback)
    asyncio.create_task(session_termination_monitor())
    await EachSessionOnceMonitor.async_foreach_session_create_task(app, prompt_monitor)


logger.debug("running forever!")
run_forever(main, retry=True)
