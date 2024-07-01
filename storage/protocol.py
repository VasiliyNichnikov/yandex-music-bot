import typing
from typing import Protocol

from requests_to_music_service.protocol import RequestToServiceProtocol
from storage.data import PlaylistEntry, TrackData, AlbumData, ShortAlbumData


class TracksStorageProtocol(Protocol):
    """
        Хранилище для получения треков и общей информации
    """

    @property
    def total_number_of_tracks(self) -> int:
        """
            Возвращает общее количество треков
        """
        raise NotImplemented

    async def add(self, request: RequestToServiceProtocol) -> bool:
        raise NotImplemented

    def try_get_album_by_id(self, album_id: int) -> ShortAlbumData | None:
        raise NotImplemented

    def get_loaded_playlists(self) -> typing.Tuple[PlaylistEntry, ...]:
        """
            Возвращает все загруженные треки
        """
        raise NotImplemented

    def get_tracks_range(self, min_value: int, max_value: int) -> typing.Tuple[TrackData, ...]:
        """
            Возвращает треки в промежутке
        """
        raise NotImplemented

    def clear(self) -> None:
        """
            Очистка загруженны данных
            Очень аккуратно использовать
        """
        raise NotImplemented
