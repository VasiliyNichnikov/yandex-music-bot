import asyncio
import typing

from core.config import ConfigManager
from core.log_utils import get_logger
from storage.protocol import TracksStorageProtocol
from storage.data import TrackData
from yandex.protocol import CacheTracksProtocol
from yandex.protocol import TracksLoaderProtocol

logger = get_logger(__name__)


class CacheTracks(CacheTracksProtocol):

    def __init__(self, storage: TracksStorageProtocol, tracks_loader: TracksLoaderProtocol, config: ConfigManager) -> None:
        self._storage: TracksStorageProtocol = storage
        # Кэш загруженных треков.
        self._loaded_tracks: typing.Dict[int, TrackData] = {}
        self._tracks_loader: TracksLoaderProtocol = tracks_loader
        self._config = config

    def get_any_tracks_in_range(self, min_value: int, max_value: int) -> typing.List[TrackData]:
        tracks = self._storage.get_tracks_range(min_value, max_value)
        available_tracks = [track for track in tracks if track.available]
        return available_tracks

    async def get_downloaded_tracks_in_range(self, min_value: int, max_value: int) -> typing.List[TrackData]:
        tracks = self._storage.get_tracks_range(min_value, max_value)

        result = []
        # Треки которые необходимо загрузить
        tracks_to_download = []
        for track in tracks:
            track_id = track.id
            # Трек уже загружен
            if track_id in self._loaded_tracks:
                loaded_track_wrapper = self._loaded_tracks[track_id]
                result.append(loaded_track_wrapper)
            else:
                tracks_to_download.append(track)

        if len(tracks_to_download) != 0:
            tasks = []

            # Треки, поставленные на загрузку
            loading_tracks = []
            for track_to_download in tracks_to_download:
                if not track_to_download.available:
                    continue

                if self._config["loading_tracks_into_ram"]:
                    coro = self._tracks_loader.upload_track_to_RAM(track_to_download)
                else:
                    coro = self._tracks_loader.upload_track_to_hard_drive(track_to_download)
                task = asyncio.create_task(coro)
                tasks.append(task)
                loading_tracks.append(track_to_download)

            await asyncio.gather(*tasks)

            for track, task in zip(loading_tracks, tasks):
                # Трек не был загружен
                if not task.result():
                    continue

                self._loaded_tracks[track.id] = track
                result.append(track)
        return result

    def free(self) -> None:
        self._loaded_tracks.clear()
