"""
        Проверяем доступы
        Работает только во DiscordViewHelper
"""

import typing

from core.log_utils import get_logger
from permissions.errors import FailedToInitializeDiscordViewHelper

logger = get_logger(__name__)


def check_permissions_view(func: typing.Callable[[int | None, int | None], None]):
    def wrapper(*args):
        # Костыли
        from core.thread import UserThread
        from core.view import DiscordViewHelper

        if len(args) == 0:
            raise TypeError("The number of arguments must be greater than one.")

        if not isinstance(args[0], DiscordViewHelper):
            raise TypeError(f"Invalid data type: {type(args[0])}.")

        thread: UserThread = args[0]._thread
        guild = thread.guild
        permissions = guild.me.guild_permissions

        check = permissions.manage_channels and permissions.send_messages and permissions.manage_messages
        if check:
            return func(*args)

        raise FailedToInitializeDiscordViewHelper("There are not enough rights for initialization.")

    return wrapper

