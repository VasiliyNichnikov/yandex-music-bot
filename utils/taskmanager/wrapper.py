"""
    Оборачиваем асинхронные методы и функции
    И подключает аргументы при вызове
"""
import typing

from core.log_utils import get_logger

logger = get_logger(__name__)


class Wrapper:
    def __init__(self) -> None:
        self._func: typing.Callable[[typing.Any], typing.Any] | None = None
        self._args = None

    def set_func(self, func: typing.Callable, **kwargs) -> None:
        if self._func is not None:
            logger.warning("Func is already initialized.")

        if self._args is not None:
            logger.warning("Args is already initialized.")

        self._func = func
        self._args = kwargs

    async def task(self) -> None:
        if self._func is None:
            logger.error("Func is not initialized.")
            return

        await self._func(**self._args)
