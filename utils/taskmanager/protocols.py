from asyncio import Protocol

from utils.taskmanager.wrapper import Wrapper


class TaskWrapperProtocol(Protocol):

    def cancel(self) -> None:
        pass

    async def perform(self) -> None:
        pass


class TaskManagerProtocol(Protocol):
    def add_task(self, wrapper: Wrapper, name: str | None = None) -> TaskWrapperProtocol:
        pass
