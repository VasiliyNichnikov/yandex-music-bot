"""
    Отвечает за блокировку
"""
import inspect
from typing import Protocol, runtime_checkable


@runtime_checkable
class BlockerSupported(Protocol):

    @property
    def is_blocked(self) -> bool:
        raise NotImplemented


class Blocker:
    def __init__(self) -> None:
        self._is_blocked: bool = False

    def is_blocked(self) -> bool:
        return self._is_blocked

    def block(self) -> None:
        self._is_blocked = True

    def unlock(self) -> None:
        self._is_blocked = False


def check_lock(func):
    async def empty_async(*args, **kwargs) -> None:
        pass

    def empty(*args, **kwargs) -> None:
        pass

    def wrapper(*args, **kwargs):
        if len(args) == 0:
            raise TypeError("The number of arguments must be greater than one.")

        if not isinstance(args[0], BlockerSupported):
            raise TypeError(f"Invalid data type: {type(args[0])}.")

        blocker: BlockerSupported = args[0]
        if not blocker.is_blocked:
            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return empty_async(*args, **kwargs)
        return empty(*args, **kwargs)

    return wrapper
