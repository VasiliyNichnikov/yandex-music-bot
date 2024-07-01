import asyncio

from utils.taskmanager.protocols import TaskWrapperProtocol
from utils.taskmanager.wrapper import Wrapper


class TaskWrapperEmpty(TaskWrapperProtocol):
    """
        Пустышка
    """
    def cancel(self) -> None:
        pass

    async def perform(self) -> None:
        pass


class TaskWrapperDefault(TaskWrapperProtocol):
    def __init__(self, task_manager: "TaskManager", wrapper: Wrapper, name: str = None) -> None:
        self._task_manager: "TaskManager" = task_manager
        self._wrapper: Wrapper = wrapper
        self._task_being_performed: asyncio.Task | None = None
        self._name: str | None = name

    async def perform(self) -> None:
        try:
            coro = self._wrapper.task()
            self._task_being_performed = asyncio.create_task(coro)
            await self._task_being_performed
        except asyncio.CancelledError:
            pass

    def cancel(self) -> None:
        if self._task_manager.contains_task_in_queue(self):
            self._task_manager.remove_task(self)

        if self._task_being_performed is not None:
            self._task_being_performed.cancel()
            self._task_being_performed = None

    def __str__(self) -> str:
        name = self._name if self._name is not None else "None"
        return name
