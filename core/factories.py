import typing

from discord import Guild

from core.config import ConfigManager
from database.clients import ThreadDataBase
from requests_to_music_service.data import InfoAboutRequest
from requests_to_music_service.executing_requests import ExecutingRequests
from storage.storage import Storage
from yandex.cache import CacheTracks


class BotFactory:
    def __init__(self, bot: "CactusDiscordBot", config: ConfigManager) -> None:
        self._bot: "CactusDiscordBot" = bot
        self._config: ConfigManager = config

    def create_recent_listened_tracks_view(self) -> "RecentlyListenedTracksView":
        from core.view import RecentlyListenedTracksView

        return RecentlyListenedTracksView(self._bot.try_search_and_complete_command)

    def create_thread(self, guild: Guild) -> "UserThread":
        from core.thread import UserThread

        db_api = ThreadDataBase(self._bot.config, self._bot.database_api, guild.id)
        return UserThread(guild, db_api, self._bot.config, self._bot.factory, self._bot.message_manager, self._bot.slash_commands)

    def create_player(self, timer: "Timer", view: "DiscordViewHelper",
                      on_add_request_action: typing.Callable[[InfoAboutRequest], None]) -> "PlayerFacade":
        from core.playerfacade import PlayerFacade
        from yandex.collector import TrackQueueManager

        number_attempts = self._config["number_of_attempts_when_requesting_music_service"]
        delay_between_errors = self._config["delay_in_case_of_error_when_requesting_music_service"]

        executing = ExecutingRequests(number_attempts, delay_between_errors)
        storage = Storage(executing)
        cache_tracks = CacheTracks(storage, self._bot.yandex_music_api, self._config)
        queue_manager = TrackQueueManager(self._bot.config["max_tracks_in_list"], self._bot.task_manager,
                                          storage,
                                          cache_tracks)
        player = PlayerFacade(timer, on_add_request_action, queue_manager, view, self._bot.task_manager, storage)
        return player

    def create_timer(self, waiting_time: int) -> "Timer":
        from core.timer import Timer

        return Timer(waiting_time, self._bot.task_manager)
