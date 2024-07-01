import typing

from core.config import ConfigManager
from core.log_utils import get_logger

logger = get_logger(__name__)


class InitializedSlashCommands:
    def __init__(self, config: ConfigManager) -> None:
        self._commands: typing.Dict[str, int] = {}
        self._config = config

    def add_command(self, name, command_id) -> None:
        if name in self._commands:
            logger.error(f"Command {name} is already in the dictionary.")
            return
        self._commands[name] = command_id

    def __getitem__(self, key: str) -> typing.Any:
        if not self._config["slash_supported"]:
            return 0

        return self.get(key)

    def get(self, key: str) -> typing.Any:
        if not self._config["slash_supported"]:
            return 0

        value = self._commands[key]
        return value
