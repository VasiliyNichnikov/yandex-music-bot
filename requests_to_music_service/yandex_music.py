import os.path
import typing

from core.builders import YandexBuilderUrl
# yandex api
from core.log_utils import get_logger
from yandex_music import Album, Playlist, Artist, Track, ArtistTracks

import requests_to_music_service.data as iar
from requests_to_music_service.data import InfoAboutRequest
from requests_to_music_service.protocol import RequestToServiceProtocol, RequestToInstallTrack
from storage.data import AnswerFromMusicService, AlbumData, TrackData, ShortArtistData, PlaylistData, ShortAlbumData, \
    ArtistData
from yandex.errors import YandexMusicDataCouldNotBeFound
from yandex.requests import RequestToYandexMusicBase

logger = get_logger(__name__)


class RequestToYandexMusicService(RequestToServiceProtocol):
    """
        Запрос для получения данных с музыкальных сервисов
        Сейчас только для Я.Музыка
    """
    @property
    def is_loaded(self) -> bool:
        return self._loaded_data is not None

    def __init__(self, yandex_request: RequestToYandexMusicBase) -> None:
        self._yandex_request: RequestToYandexMusicBase = yandex_request
        self._loaded_data: AnswerFromMusicService | None = None

    def try_get_info_about_request(self) -> InfoAboutRequest | None:
        if not self.is_loaded:
            return None

        url = self.__get_request_url()
        if self._loaded_data.album:
            album = self._loaded_data.album
            if len(self._loaded_data.album.tracks) == 1:
                first_track = self._loaded_data.album.tracks[0]
                return iar.create_for_one_track(first_track.title, url, album.title)

            return iar.create_for_album(album.title, url)

        if self._loaded_data.playlist:
            playlist = self._loaded_data.playlist
            if len(self._loaded_data.playlist.tracks) == 1:
                first_track = self._loaded_data.playlist.tracks[0]
                album = self.__try_get_short_album(first_track.id)
                if album is not None:
                    return iar.create_for_one_track(first_track.title, url, album.title)

            return iar.create_for_playlist(playlist.title, url, playlist.user_name)

        if self._loaded_data.artist:
            artist = self._loaded_data.artist
            return iar.create_for_artist(artist.name, url)

        logger.error("album and playlist and artist is None.")
        return iar.create_empty()

    def get_loaded_data(self) -> AnswerFromMusicService | None:
        return self._loaded_data

    async def perform(self) -> bool:
        try:
            data = await self._yandex_request.get_data()

            if data is None:
                logger.error("perform: data is None.")
                return False

            loaded_albums: typing.List[ShortAlbumData] = []
            album: AlbumData | None = None
            playlist: PlaylistData | None = None
            artist: ArtistData | None = None

            if data.artist is not None:
                artist_tracks: ArtistTracks = await data.artist.get_tracks_async(page_size=100)
                artist = self.__get_artist_data(data.artist, artist_tracks, loaded_albums)
            if data.album is not None:
                album = self.__get_album(data.album, loaded_albums)
            if data.playlist is not None:
                playlist = self.__get_playlist(data.playlist, loaded_albums)
            if data.track is not None:
                album = self.__wrap_track_in_album(data.track, loaded_albums)
            if data.search_tracks is not None:
                album = self.__wrap_track_in_album(data.search_tracks, loaded_albums)

            if album is None and playlist is None and artist is None:
                logger.error("perform: album and playlist and artist is none.")
                return False

            self._loaded_data = AnswerFromMusicService(playlist=playlist,
                                                       album=album,
                                                       artist=artist,
                                                       loaded_albums=tuple(loaded_albums))
            return True
        except YandexMusicDataCouldNotBeFound:
            # данные не найдены, смысла загружать нет, поэтому сделаем вид, что загрузили
            return True
        except Exception as e:
            logger.error(f"perform: error during execution: {e}")
            return False

    def __get_playlist(self, playlist: Playlist, all_albums: typing.List[ShortAlbumData]) -> PlaylistData:
        owner_id = playlist.uid
        playlist_id = playlist.kind
        user_login = playlist.owner.login
        user_name = playlist.owner.name
        title = playlist.title
        available = playlist.available
        cover_uri: str | None = playlist.cover.uri if playlist.cover is not None else None
        tracks: typing.List[TrackData] = [self.__get_track(short.track, all_albums) for short in playlist.tracks]

        return PlaylistData(owner_id=owner_id,
                            user_login=user_login,
                            user_name=user_name,
                            playlist_id=playlist_id,
                            title=title,
                            available=available,
                            cover_uri=cover_uri,
                            tracks=tuple(tracks))

    def __get_album(self, album: Album, all_albums: typing.List[ShortAlbumData]) -> AlbumData:
        album_id = album.id
        title = album.title
        artists = tuple(self.__get_artist(artist) for artist in album.artists)
        available = album.available
        cover_uri = album.cover_uri
        volumes = album.volumes
        tracks: typing.List[TrackData] = []

        if volumes is not None:
            for volume in volumes:
                tracks.extend([self.__get_track(track, all_albums) for track in volume])

        return AlbumData(id=album_id,
                         title=title,
                         artists=artists,
                         available=available,
                         cover_uri=cover_uri,
                         track_count=len(tracks),
                         tracks=tuple(tracks))

    def __get_track(self, track: Track, all_albums: typing.List[ShortAlbumData]) -> TrackData:
        track_id = track.id
        title = track.title
        artists = tuple(self.__get_artist(artist) for artist in track.artists)
        available = track.available
        duration = track.duration_ms
        album_ids = tuple(album.id for album in track.albums)

        for album in track.albums:
            short_album = self.__get_short_album_data(album)
            if short_album in all_albums:
                continue
            all_albums.append(short_album)

        cover_uri = track.cover_uri

        return TrackData(id=track_id,
                         title=title,
                         duration_in_milliseconds=duration,
                         available=available,
                         artists=artists,
                         cover_uri=cover_uri,
                         album_ids=album_ids)

    def __wrap_track_in_album(self, track: Track | typing.Tuple[Track], all_albums: typing.List[ShortAlbumData]) -> AlbumData | None:
        album = track.albums[0] if isinstance(track, Track) else track[0].albums[0]
        album_id = album.id
        title = album.title
        available = album.available
        cover_uri = album.cover_uri
        if isinstance(track, Track):
            track_data = (self.__get_track(track, all_albums),)
        else:
            track_data = tuple([self.__get_track(t, all_albums) for t in track])
        artists = tuple(self.__get_artist(artist) for artist in album.artists)
        return AlbumData(id=album_id,
                         title=title,
                         available=available,
                         cover_uri=cover_uri,
                         track_count=1,
                         tracks=track_data,
                         artists=artists)

    def __get_artist_data(self, artist: Artist, artist_tracks: ArtistTracks, all_albums: typing.List[ShortAlbumData]) \
            -> ArtistData:
        artist_id = artist.id
        artist_name = artist.name
        artist_available = artist.available
        artist_cover_uri = artist.cover if artist.cover is not None else None
        tracks = tuple(self.__get_track(track, all_albums) for track in artist_tracks.tracks)

        return ArtistData(id=artist_id, cover_uri=artist_cover_uri, name=artist_name, available=artist_available, tracks=tracks)

    def __get_short_album_data(self, data: Album) -> ShortAlbumData:
        album_id = data.id
        title = data.title
        available = data.available
        cover_uri = data.cover_uri
        artists = tuple(self.__get_artist(artist) for artist in data.artists)

        return ShortAlbumData(id=album_id, title=title,
                              available=available,
                              cover_uri=cover_uri,
                              artists=artists,
                              track_count=data.track_count)

    @staticmethod
    def __get_artist(artist: Artist) -> ShortArtistData:
        artist_id = artist.id
        name = artist.name.lower()
        return ShortArtistData(id=artist_id, name=name)

    def __get_request_url(self) -> str | None:
        if not self.is_loaded:
            return None

        builder = YandexBuilderUrl()
        if self._loaded_data.album:
            builder.set_album_id(self._loaded_data.album.id)
            if len(self._loaded_data.album.tracks) == 1:
                first_track_id = self._loaded_data.album.tracks[0].id
                builder.set_track_id(first_track_id)
            return builder.get_result()

        if self._loaded_data.playlist:
            if len(self._loaded_data.playlist.tracks) == 1:
                first_track = self._loaded_data.playlist.tracks[0]
                album_id: int | None = first_track.album_ids[0] if len(first_track.album_ids) > 0 else None
                first_track_id = first_track.id

                if album_id is None:
                    logger.error(f"album for track {first_track.title} (id: {first_track.id}) not found.")
                else:
                    builder.set_album_id(album_id)
                    builder.set_track_id(first_track_id)
                    return builder.get_result()

            user_login = self._loaded_data.playlist.user_login
            playlist_id = self._loaded_data.playlist.playlist_id
            builder.set_playlist_id(user_login, playlist_id)
            return builder.get_result()

        if self._loaded_data.artist:
            artist_id = self._loaded_data.artist.id
            builder.set_artist_id(artist_id)
            return builder.get_result()

        logger.error("album and playlist and artist is None.")
        return None

    def __try_get_short_album(self, album_id: int) -> ShortAlbumData | None:
        if not self.is_loaded:
            return None

        for album in self._loaded_data.loaded_albums:
            if album.id == album_id:
                return album
        return None



class RequestToInstallYandexTrack(RequestToInstallTrack):

    def __init__(self, track: Track, ram: bool, path: str | None) -> None:
        self._track: Track = track
        self._ram: bool = ram
        self._path: str | None = path

    @property
    def is_loaded(self) -> bool:
        if not self._ram and self._path is not None:
            return os.path.exists(self._path)
        # TODO: доработать для Ram
        return False

    async def perform(self) -> bool:
        if self._ram:
            await self._track.download_bytes_async()
        else:
            if self._path is None:
                logger.error("ram is turned off but the path is not found")
                return False
            await self._track.download_async(self._path)
        return True




