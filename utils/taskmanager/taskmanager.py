import asyncio
import typing

from core.log_utils import get_logger
from utils.taskmanager.protocols import TaskManagerProtocol
from utils.taskmanager.taskwrapper import TaskWrapperProtocol, TaskWrapperEmpty, TaskWrapperDefault
from utils.taskmanager.wrapper import Wrapper

logger = get_logger(__name__)


class TaskManager(TaskManagerProtocol):
    def __init__(self) -> None:
        self._tasks: typing.List[TaskWrapperProtocol] = []
        self._delay = 0.5  # Задержка между задачами

    def add_task(self, wrapper: Wrapper, name: str | None = None) -> TaskWrapperProtocol:
        task = TaskWrapperDefault(self, wrapper, name)
        if task in self._tasks:
            logger.error("The task already exists in list.")
            return TaskWrapperEmpty()
        self._tasks.append(task)
        return task

    async def process(self) -> None:
        """
            Выполняем все задачи, которые были переданы в обработку
        """
        if len(self._tasks) == 0:
            return

        while len(self._tasks) > 0:
            first_task = self._tasks.pop(0)
            asyncio.ensure_future(first_task.perform())
            await asyncio.sleep(self._delay)

    def contains_task_in_queue(self, task: TaskWrapperProtocol) -> bool:
        return task in self._tasks

    def remove_task(self, task: TaskWrapperProtocol) -> None:
        if task is None:
            logger.warning("Removed task is None")
            return

        if task not in self._tasks:
            logger.error(f"Task (name: {task}) not found in list.")
            return

        self._tasks.remove(task)
