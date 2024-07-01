import typing
from typing import Protocol

from storage.data import TrackData


class CacheTracksProtocol(Protocol):
    """
        Сохраняет треки в кэше
        Является оберткой над requests
    """

    def get_any_tracks_in_range(self, min_value: int, max_value: int) -> typing.List[TrackData]:
        """
            Возвращает все треки, среди треков могут быть и не загруженные
        """
        raise NotImplemented

    async def get_downloaded_tracks_in_range(self, min_value: int, max_value: int) -> typing.List[TrackData]:
        """
            Получает треки в промежутке + догружает при необходимости
        """
        raise NotImplemented

    def free(self) -> None:
        """
            Освобождение памяти
        """
        raise NotImplemented


class TracksLoaderProtocol(Protocol):
    """
        Загрузчик треков в ОЗУ или по заданному пути
    """

    async def upload_track_to_RAM(self, track: TrackData) -> bool:
        """
            Загрузка трека в ОЗУ
        """
        raise NotImplemented

    async def upload_track_to_hard_drive(self, track: TrackData) -> bool:
        """
            Загрузка трека на жесткий диск
        """
        raise NotImplemented
