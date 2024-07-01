import asyncio
import math
import sys
import typing
from typing import Protocol

from core.log_utils import get_logger
from storage.protocol import TracksStorageProtocol
from utils.taskmanager.taskmanager import TaskWrapperProtocol, TaskManagerProtocol
from utils.taskmanager.wrapper import Wrapper
from yandex.errors import TracksAlreadyBeingUploaded
from yandex.protocol import CacheTracksProtocol
from yandex.utils import get_track_wrapper
from yandex.track import TrackWrapperBase

logger = get_logger(__name__)


class TrackQueue(Protocol):

    @property
    def is_empty(self) -> bool:
        raise NotImplemented

    def get_next_track(self) -> TrackWrapperBase | None:
        raise NotImplemented

    def get_all_next_tracks(self) -> typing.Tuple[TrackWrapperBase]:
        """
            Возвращает все следующие треки, которые есть в очереди
            ВАЖНО: треки не доступны для прослушивания и нужны только для отображения
        """
        raise NotImplemented

    def add_track_first_to_queue(self, track: TrackWrapperBase) -> None:
        raise NotImplemented

    def update_queue(self, on_complete_action: typing.Callable[[], None] | None) -> None:
        raise NotImplemented


class TrackQueueManager(TrackQueue):
    def __init__(self, max_tracks_in_list: int, task_manager: TaskManagerProtocol,
                 storage: TracksStorageProtocol,
                 cache: CacheTracksProtocol) -> None:
        self._queue_tracks: typing.List[TrackWrapperBase] = []

        self._storage = storage
        self._cache: CacheTracksProtocol = cache

        # В ОЗУ будем хранить не более max_tracks_in_list треков за раз
        self._max_tracks_in_list: int = max_tracks_in_list
        self._download_task: asyncio.Task | TaskWrapperProtocol | None = None
        self._task_manager: TaskManagerProtocol = task_manager

        # С какого трека начинаем закачку
        self._current_track_index: int = 0

        # Максимально возможное количество треков, которое намерены грузить
        self._max_tracks_in_list: int = max_tracks_in_list

    @property
    def is_loading(self) -> bool:
        return self._download_task is not None

    @property
    def is_empty(self) -> bool:
        return len(self._queue_tracks) == 0

    @property
    def is_queue_tracks_empty(self) -> bool:
        return len(self._queue_tracks) == 0

    def add_track_first_to_queue(self, track: TrackWrapperBase) -> None:
        self._queue_tracks.insert(0, track)

    def get_next_track(self) -> TrackWrapperBase | None:
        if len(self._queue_tracks) == 0:
            return None

        first_track = self._queue_tracks.pop(0)
        return first_track

    def get_all_next_tracks(self) -> typing.Tuple[TrackWrapperBase]:
        current_track_index = self._current_track_index - len(self._queue_tracks)
        if current_track_index < 0:
            logger.error("get_all_next_tracks: current track index < 0.")
            current_track_index = 0

        tracks = self._cache.get_any_tracks_in_range(current_track_index, current_track_index + sys.maxsize)

        wrappers = tuple(get_track_wrapper(track, self._storage) for track in tracks)
        return wrappers

    def update_queue(self, on_complete_action: typing.Callable[[], None] | None) -> None:
        if self._download_task is not None:
            return

        wrapper = Wrapper()
        if on_complete_action is not None:
            wrapper.set_func(self.__upload_tracks_to_queue_with_action, on_complete_action=on_complete_action)
        else:
            wrapper.set_func(self.__upload_tracks_to_queue_without_action)
        self._download_task = self._task_manager.add_task(wrapper, name="update_queue")

    async def upload_queue_async(self) -> None:
        if self._download_task is not None:
            raise TracksAlreadyBeingUploaded("Tracks are being loaded!")

        self._download_task = asyncio.create_task(self.__upload_tracks_to_queue())
        await self._download_task
        self._download_task = None

    async def __upload_tracks_to_queue(self) -> None:
        if len(self._queue_tracks) >= self._max_tracks_in_list:
            return

        number_of_tracks_uploaded = len(self._queue_tracks)
        number_tracks_to_download = self._max_tracks_in_list - number_of_tracks_uploaded

        if number_tracks_to_download == 0:
            logger.warning("No tracks found to download")
            return

        if number_tracks_to_download < 0:
            logger.error(f"Invalid value: number tracks to download: {number_tracks_to_download}.\n"
                         f"Max tracks in list: {self._max_tracks_in_list};"
                         f"Number of tracks uploaded: {number_tracks_to_download}")
            return

        tracks = await self._cache.get_downloaded_tracks_in_range(self._current_track_index,
                                                                  self._current_track_index + number_tracks_to_download)

        wrappers = [get_track_wrapper(track, self._storage) for track in tracks]

        self._queue_tracks.extend(wrappers)
        if len(tracks) >= number_tracks_to_download and len(tracks) != number_tracks_to_download:
            logger.error(f"The number of tracks does not match the set ones. "
                         f"Downloaded tracks: {len(tracks)}; "
                         f"Number tracks to download: {number_tracks_to_download}")

        # Обязательно len(tracks), а не number_tracks_to_download
        # Так как не всегда мы загружаем именно столько треков сколько было передано в number_tracks_to_download
        self._current_track_index += len(tracks)

    async def __upload_tracks_to_queue_with_action(self, on_complete_action: typing.Callable[[], None]) -> None:
        await self.__upload_tracks_to_queue_without_action()
        on_complete_action()

    async def __upload_tracks_to_queue_without_action(self) -> None:
        await self.__upload_tracks_to_queue()
        self._download_task = None

    def clear(self) -> None:
        self._current_track_index = 0
        self._queue_tracks.clear()

        if self._download_task is not None:
            self._download_task.cancel()
            self._download_task = None
