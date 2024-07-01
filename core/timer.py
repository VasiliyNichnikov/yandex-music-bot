import asyncio
import inspect
import math
import time
from typing import Callable

from core.log_utils import get_logger
from utils.taskmanager.protocols import TaskManagerProtocol, TaskWrapperProtocol
from utils.taskmanager.wrapper import Wrapper

logger = get_logger(__name__)


class Timer:
    def __init__(self, waiting_time: int | float, task_manager: TaskManagerProtocol) -> None:
        self._waiting_time: int = waiting_time
        self._invoke: None | Callable = None
        self._delay = 0.1
        self._task: None | TaskWrapperProtocol = None
        self._task_manager: TaskManagerProtocol = task_manager

        self._end_time: int | None = None

    @property
    def remaining_time(self) -> int:
        if self._end_time is None:
            logger.error("Timer has not")
            return 0
        current_time = math.ceil(time.time())
        remaining_time = self._end_time - current_time
        if remaining_time < 0:
            logger.error("The remaining time is less than 0")
            return 0
        return remaining_time

    def set_invoke(self, invoke: Callable) -> None:
        self._invoke = invoke

    def start(self) -> None:
        if self._task is not None:
            logger.warning("Timer already running.")
            return

        wrapper = Wrapper()
        wrapper.set_func(self.__start_async)
        self._task = self._task_manager.add_task(wrapper, name="start: start_async")

    async def __start_async(self) -> None:
        await self.__countdown()
        self._task = None
        logger.info("Timer completed.")
        if self._invoke is None:
            logger.error("Invoke is none.")
            return
        if inspect.iscoroutinefunction(self._invoke):
            await self._invoke()
        else:
            self._invoke()

    async def __countdown(self) -> None:
        start_time = math.ceil(time.time())
        self._end_time = start_time + self._waiting_time
        current_time = math.ceil(time.time())
        while self._end_time >= current_time:
            await asyncio.sleep(self._delay)
            current_time = math.ceil(time.time())

    def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        self._task = None
        self._end_time = None

