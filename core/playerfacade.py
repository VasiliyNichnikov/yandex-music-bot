"""
    Отвечает за добавление треков в очередь,
    Проигрывания треков,
    Отображение текущего трека
"""
import typing

from discord import VoiceClient

from core.blocker import Blocker
from core.errors import PlayerCriticalError
from core.player import Player
from core.protocol import PlayerProtocol
from core.timer import Timer
from core.log_utils import get_logger
from core.view import DiscordViewHelper
from requests_to_music_service.data import InfoAboutRequest
from requests_to_music_service.protocol import RequestToServiceProtocol
from utils.taskmanager.protocols import TaskManagerProtocol, TaskWrapperProtocol
from utils.taskmanager.wrapper import Wrapper
from yandex.collector import TrackQueueManager
from yandex.track import TrackWrapperBase
from storage.protocol import TracksStorageProtocol

logger = get_logger(__name__)


class PlayerFacade(PlayerProtocol):
    def __init__(self, disconnection_time: Timer,
                 on_add_request_action: typing.Callable[[InfoAboutRequest], None],
                 queue_manager: TrackQueueManager,
                 view: DiscordViewHelper,
                 task_manager: TaskManagerProtocol,
                 storage: TracksStorageProtocol) -> None:

        self._disconnection_time: Timer = disconnection_time
        self._on_add_request_action: typing.Callable[[InfoAboutRequest], None] = on_add_request_action
        self._queue_manager: TrackQueueManager = queue_manager
        self._view: DiscordViewHelper = view
        self._task_manager: TaskManagerProtocol = task_manager
        self._storage = storage
        # Не очень нравиться, так как создает кучу проверок в каждом методе
        self._blocker: Blocker = Blocker()

        self._player: Player = Player(queue_manager, task_manager)
        self._player.set_track_started_action(self.__track_started)
        self._player.set_track_completed_action(self.__track_completed)

        # Задачи
        self._track_started_task: TaskWrapperProtocol | None = None

    def is_loop(self) -> bool:
        return self._player.is_loop_track

    def is_running(self) -> bool:
        return self._player.is_running

    def is_paused(self) -> bool:
        return self._player.is_paused

    async def preview_track(self) -> None:
        if self._blocker.is_blocked():
            return

        if self._player.is_played_tracks_empty:
            await self._view.send_message_not_tracks_in_previous()
            return

        # Блокируем
        self._blocker.block()
        try:
            self._disconnection_time.stop()

            self._player.set_preview_track()
            self._player.play_current_track()

        except Exception as e:
            logger.error(f"Preview track: Player exception: {e};", exc_info=True)
            await self.__stop_during_critical_error()
            raise PlayerCriticalError("Preview track: exception occurred.")
        finally:
            # Разблокируем
            self._blocker.unlock()

    async def next_track(self, add_to_queue: bool = False) -> None:
        if self._blocker.is_blocked():
            return

        if self._queue_manager.is_empty:
            await self._view.send_message_not_tracks_in_queue()
            return

        # Блокируем
        self._blocker.block()

        try:
            self._disconnection_time.stop()

            if self._player.is_running and add_to_queue:
                # Разблокируем
                self._blocker.unlock()
                return

            self._player.set_next_track()
            self._player.play_current_track()

        except Exception as e:
            logger.error(f"Next track: Player exception: {e};", exc_info=True)
            await self.__stop_during_critical_error()
            raise PlayerCriticalError("Next track: exception occurred.")
        finally:
            # Разблокируем
            self._blocker.unlock()

    async def pause_track(self) -> None:
        if self._blocker.is_blocked():
            return

        # Блокируем
        self._blocker.block()

        try:
            if self._player.is_playing:
                self._player.pause()
                self._disconnection_time.start()
            elif self._player.is_paused:
                self._player.resume()
                self._disconnection_time.stop()
        except Exception as e:
            logger.error(f"Pause track: Player exception: {e};", exc_info=True)
            await self.__stop_during_critical_error()
            raise PlayerCriticalError("Pause track: exception occurred.")
        finally:
            # Разблокируем
            self._blocker.unlock()

    async def stop_track(self, disconnect: bool, safely: bool = False) -> None:
        if self._blocker.is_blocked():
            return

        # Блокируем
        self._blocker.block()

        try:
            self._player.stop(safely=safely)
            self._queue_manager.clear()

            # При отключение, не запускаем таймер
            if disconnect:
                self._disconnection_time.stop()
            else:
                self._disconnection_time.start()
            await self._view.update_cover_to_default()
        except Exception as e:
            logger.error(f"Stop track: Player exception: {e};", exc_info=True)
            await self.__stop_during_critical_error(disconnect=disconnect)
            raise PlayerCriticalError("Stop track: exception occurred.")
        finally:
            # Очень аккуратно. Лучше только тут и вызывать
            self._storage.clear()
            # Разблокируем
            self._blocker.unlock()

    async def show_track_queue(self) -> None:
        next_tracks = self._queue_manager.get_all_next_tracks()
        await self._view.show_track_queue(next_tracks)

    async def change_loop(self, show_message: bool = True) -> None:
        self._player.change_loop()

        if show_message is False:
            return

        if self._player.is_loop_track:
            await self._view.show_enable_loop()
        else:
            await self._view.show_disable_loop()

    def update_voice_client(self, voice_client: VoiceClient) -> None:
        self._player.update_voice_client(voice_client)

    async def add_track_request_and_play(self, request: RequestToServiceProtocol) -> None:
        self._disconnection_time.stop()
        state = await self._storage.add(request)
        if not state:
            await self._view.send_message_not_tracks_in_queue()
            return

        if not self._queue_manager.is_loading:
            await self._queue_manager.upload_queue_async()
        await self.next_track(add_to_queue=True)

        info_about_request = request.try_get_info_about_request()
        if info_about_request is not None:
            self._on_add_request_action(info_about_request)

    def __track_started(self, track: TrackWrapperBase) -> None:
        if self._track_started_task is not None:
            self._track_started_task.cancel()
            self._track_started_task = None

        wrapper = Wrapper()
        wrapper.set_func(self.__update_cover, track=track)
        self._track_started_task = self._task_manager.add_task(wrapper, name="track_started: update cover")

    def __track_completed(self, track: TrackWrapperBase) -> None:
        if self._player.is_loop_track:
            return

        history_wrapper = Wrapper()
        history_wrapper.set_func(self.__add_track_to_history, track=track)
        self._task_manager.add_task(history_wrapper, name="track_completed: history")

        if self._queue_manager.is_empty:
            stop_wrapper = Wrapper()
            stop_wrapper.set_func(self.stop_track, disconnect=False)
            self._task_manager.add_task(stop_wrapper, name="track_completed: stop")

    async def __stop_during_critical_error(self, disconnect: bool = False) -> None:
        logger.critical("A critical error occurred during operation")

        try:
            self._player.stop(safely=False)
            self._queue_manager.clear()

            # При отключение, не запускаем таймер
            if disconnect:
                self._disconnection_time.stop()
            else:
                self._disconnection_time.start()

            await self._view.update_cover_to_default()
        except Exception:
            pass

    async def __update_cover(self, track: TrackWrapperBase) -> None:
        await self._view.update_cover_for_selected_track(track)

    async def __add_track_to_history(self, track: TrackWrapperBase) -> None:
        await self._view.add_track_to_history(track)