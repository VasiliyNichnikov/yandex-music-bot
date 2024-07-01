import re
import typing
from abc import ABC, abstractmethod

import yandex_music.exceptions
from yandex_music import ClientAsync, Track, Album, Artist, ChartInfo
from yandex_music import Playlist, Search

from core.config import ConfigManager
from core.enumes import MusicCommandType
from core.log_utils import get_logger
from yandex.data import YandexMusicRequestData
from yandex.errors import YandexMusicDataCouldNotBeFound
from yandex.utils import pattern_yandex_body

logger = get_logger(__name__)


class RequestToYandexMusicBase(ABC):
    def __init__(self, config: ConfigManager, ym_client: ClientAsync, max_tracks: int | None) -> None:
        self._config = config
        self._client = ym_client
        self._max_tracks = max_tracks

    @abstractmethod
    async def get_data(self) -> YandexMusicRequestData:
        """
            Возвразает данные в зависимости от запроса
        """
        raise NotImplemented


class RequestToYandexMusicEmpty(RequestToYandexMusicBase):
    def __init__(self, config: ConfigManager, ym_client: ClientAsync, max_tracks: int | None) -> None:
        super().__init__(config, ym_client, max_tracks)

    async def get_data(self) -> YandexMusicRequestData:
        raise NotImplemented


class RequestForTracksByUrl(RequestToYandexMusicBase):

    def __init__(self, config: ConfigManager, ym_client: ClientAsync, url: str, max_tracks: int | None) -> None:
        super().__init__(config, ym_client, max_tracks)
        self._url = url

    async def get_data(self) -> YandexMusicRequestData | None:
        data_about_url = self.__get_info_about_url(self._url)
        keys = data_about_url.keys()

        artist: Artist | None = None
        playlist: Playlist | None = None
        track: Track | None = None
        album: Album | None = None

        try:
            if "track" in keys:
                track_id = data_about_url["track"]
                track = await self.__get_track(track_id)
            if "album" in keys:
                album_id = data_about_url["album"]
                album = await self.__get_album(album_id)
            if "playlists" in keys:
                owner_id = data_about_url["users"]
                playlist_id = data_about_url["playlists"]
                playlist = await self.__get_playlist(owner_id, playlist_id)
            if "artist" in keys:
                artist_id = data_about_url["artist"]
                artist = await self.__get_artist(artist_id)
            if "chart" in self._url:
                playlist = await self.__get_chart()
        except yandex_music.exceptions.NotFoundError:
            raise YandexMusicDataCouldNotBeFound()
        except Exception as error:
            logger.error(f"RequestForTracksByUrl.data: exception: {error};", exc_info=True)
            return None

        data = YandexMusicRequestData(command_type=MusicCommandType.URL,
                                      artist=artist,
                                      album=album,
                                      playlist=playlist,
                                      track=track,
                                      search_tracks=None)
        return data

    @staticmethod
    def __get_info_about_url(url: str) -> dict:
        # Сначала смотрим на начала строки
        found_match_body = re.match(pattern_yandex_body, url)
        if found_match_body is None:
            return {}
        if url.startswith(found_match_body.group(0)) is False:
            return {}
        url = url.replace(found_match_body.group(0), '')
        # После этого смотрим на конец строки
        found_questions = url.find('?')
        if found_questions != -1:
            url = url[:found_questions]
        parts_url = url.split('/')

        number_data = len(parts_url)
        result = {}
        for index_key, index_value in zip(range(0, number_data, 2), range(1, number_data, 2)):
            result[parts_url[index_key]] = parts_url[index_value]
        return result

    async def __get_track_from_album(self, track_id) -> typing.List[Track]:
        return await self._client.tracks(track_id)

    async def __get_tracks_from_album(self, album_id) -> typing.List[Track]:
        album: Album = await self._client.albums_with_tracks(album_id)
        tracks: list[Track] = []
        for volume in album.volumes:
            for track in volume:
                tracks.append(track)
        return tracks

    async def __get_tracks_from_playlist(self, owner, playlist_id) -> typing.List[Track]:
        playlist: Playlist = await self._client.users_playlists(playlist_id, owner)
        tracks: list[Track] = [track_short.track for track_short in playlist.tracks]
        return tracks

    async def __get_tracks_from_artist(self, artist_id: int) -> typing.List[Track]:
        # На текущий момент возвращаем только первые 100 треков
        artist = await self._client.artists(artist_ids=artist_id)
        artist[0].get_tracks()
        artist_tracks = await self._client.artists_tracks(artist_id, page_size=100)
        tracks: list[Track] = [track for track in artist_tracks.tracks]
        return tracks

    async def __get_album(self, album_id: int) -> Album | None:
        """
            Возвращает альбом по id
        """
        album: Album | None = await self._client.albums_with_tracks(album_id=album_id)
        if album is None:
            logger.error(f"Album with id {album_id} is None")
            return None
        return album

    async def __get_artist(self, artist_id: int) -> Artist | None:
        """
            Возвращает артиста
        """
        artists: typing.List[Artist] = await self._client.artists(artist_id)
        if len(artists) == 0:
            logger.error(f"Artist with id {artist_id} is None")
            return None
        return artists[0]

    async def __get_chart(self) -> Playlist:
        chart_info: ChartInfo = await self._client.chart()
        playlist: Playlist = chart_info.chart
        return playlist

    async def __get_playlist(self, owner: int, playlist_id: int) -> Playlist:
        """
            Возвращает плейлист принадлежащий заданному пользователю
        """
        playlist: Playlist = await self._client.users_playlists(playlist_id, owner)
        return playlist

    async def __get_track(self, track_id: int) -> Track | None:
        """
            Возвращает трек
        """
        tracks = await self._client.tracks(track_id)
        if len(tracks) == 0:
            logger.error(f"Track with id {track_id} is None")
            return None
        return tracks[0]


class RequestForTracksBySearch(RequestToYandexMusicBase):

    def __init__(self, config: ConfigManager, ym_client: ClientAsync, search: str, max_tracks: int | None) -> None:
        super().__init__(config, ym_client, max_tracks)
        self._search = search

    async def get_data(self) -> YandexMusicRequestData:
        data = YandexMusicRequestData(command_type=MusicCommandType.SEARCH, artist=None, album=None, playlist=None,
                                      track=None, search_tracks=None)
        search_tracks: typing.List[Track] | None = None
        try:
            search_by_request: Search = await self._client.search(text=self._search, type_="track")
            tracks = search_by_request.tracks
            if tracks is None:
                return data
            results = tracks.results
            if len(results) == 0:
                return data

            search_tracks = results[:self._max_tracks]
        except yandex_music.exceptions.YandexMusicError as yandex_error:
            logger.error(f"Tracks by search (Data). Exception: {yandex_error}.", exc_info=True)
        finally:
            data.search_tracks = tuple(search_tracks)
            return data


class RequestBuilder:
    def __init__(self, config: ConfigManager) -> None:
        self._url: str | None = None
        self._search: str | None = None
        self._is_favorite = False
        self._config: ConfigManager = config
        self._max_tracks: int | None = None
        self._common_request: str | None = None  # Запрос отвечает сразу за все (Проверяет url и запросы через search)

    def set_is_favorite(self) -> "RequestBuilder":
        self._is_favorite = True
        return self

    def set_search(self, value: str) -> "RequestBuilder":
        self._search = value
        return self

    def set_url(self, value: str) -> "RequestBuilder":
        self._url = value
        return self

    def set_max_tracks(self, value: int) -> "RequestBuilder":
        if value <= 0:
            logger.error("Max tracks value must be greater than 0.")
            return self

        self._max_tracks = value
        return self

    def get_result(self, ym_client: ClientAsync) -> RequestToYandexMusicBase:
        if self._url is not None:
            return RequestForTracksByUrl(self._config, ym_client, self._url, self._max_tracks)
        if self._search is not None:
            return RequestForTracksBySearch(self._config, ym_client, self._search, self._max_tracks)

        return RequestToYandexMusicEmpty(self._config, ym_client, self._max_tracks)
