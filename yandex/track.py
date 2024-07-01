import os
import typing
from abc import ABC, abstractmethod

from core.builders import YandexBuilderUrl
from core.ffmpeg_utils import get_duration_track
from core.log_utils import get_logger
from core.path_utils import check_existence_of_file

logger = get_logger(__name__)


class ArtistBuilder:
    def __init__(self, artist_id: int, name: str) -> None:
        self._artist_id = artist_id
        self._name = name

    @property
    def artist_id(self) -> int:
        return self._artist_id

    @property
    def name(self) -> str:
        return self._name

    def build(self) -> "ArtistWrapper":
        return ArtistWrapper(self)


class ArtistWrapper:
    def __init__(self, builder: ArtistBuilder) -> None:
        self._builder = builder

    @property
    def id(self) -> int:
        return self._builder.artist_id

    @property
    def name(self) -> str:
        return self._builder.name.lower()


class AlbumBuilder:
    def __init__(self, album_id: int, title: str, track_count: int) -> None:
        self._title = title
        self._album_id = album_id
        self._track_count = track_count
        self._uri: None | str = None
        self._genre: None | str = None
        self._artists: list[ArtistWrapper] = []

    @property
    def album_id(self):
        return self._album_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def track_count(self) -> int:
        return self._track_count

    @property
    def uri(self) -> None | str:
        return self._uri

    @property
    def genre(self) -> None | str:
        return self._genre

    @property
    def artists(self) -> list[ArtistWrapper]:
        return self._artists

    def add_artist(self, artist: ArtistWrapper) -> "AlbumBuilder":
        if artist not in self._artists:
            self._artists.append(artist)
        return self

    def set_cover_uri(self, uri: str) -> "AlbumBuilder":
        self._uri = uri
        return self

    def set_genre(self, genre) -> "AlbumBuilder":
        self._genre = genre
        return self

    def build(self) -> "AlbumWrapper":
        return AlbumWrapper(self)


class AlbumWrapper:
    def __init__(self, builder: AlbumBuilder) -> None:
        self._builder = builder

    @property
    def id(self) -> int:
        return self._builder.album_id

    @property
    def title(self):
        return self._builder.title.lower()


class TrackBuilder:
    def __init__(self, track_id: int, title: str, duration_ms: int) -> None:
        self._track_id = track_id
        self._title = title
        self._uri: None | str = None
        self._duration_ms = duration_ms
        self._albums = []
        self._artists = []
        self._available_for_listening: bool = False
        self._path = ""

    @property
    def track_id(self) -> int:
        return self._track_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def uri(self) -> None | str:
        return self._uri

    @property
    def duration_ms(self) -> int:
        return self._duration_ms

    @property
    def albums(self) -> list["AlbumWrapper"]:
        return self._albums

    @property
    def artists(self) -> list["ArtistWrapper"]:
        return self._artists

    @property
    def available_for_listening(self) -> bool:
        return self._available_for_listening

    @property
    def path(self) -> str:
        return self._path

    def add_album(self, album: AlbumWrapper) -> "TrackBuilder":
        if album not in self._albums:
            self._albums.append(album)
        return self

    def add_artist(self, artist: ArtistWrapper) -> "TrackBuilder":
        if artist not in self._artists:
            self._artists.append(artist)
        return self

    def set_cover_uri(self, uri: str) -> "TrackBuilder":
        self._uri = uri
        return self

    def set_available_for_listening(self, value: bool) -> "TrackBuilder":
        self._available_for_listening = value
        return self

    def set_track_path(self, path: str) -> "TrackBuilder":
        self._path = path
        return self

    def build(self) -> "TrackWrapperBase":
        return TrackWrapper(self)


class TrackWrapperBase(ABC):
    codec: str = "mp3"
    bitrate_in_kbps: int = 192

    @property
    @abstractmethod
    def id(self) -> int:
        raise NotImplemented

    @property
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplemented

    @property
    @abstractmethod
    def albums(self) -> typing.Tuple[AlbumWrapper]:
        raise NotImplemented

    @property
    @abstractmethod
    def title(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplemented

    @abstractmethod
    def cover_url(self) -> str:
        raise NotImplemented

    @abstractmethod
    def get_filename(self) -> str | None:
        raise NotImplemented

    @abstractmethod
    def duration(self) -> float:
        raise NotImplemented

    @abstractmethod
    def duration_str(self) -> str:
        raise NotImplemented

    @abstractmethod
    def info(self, add_urls: bool) -> dict:
        raise NotImplemented

    @abstractmethod
    def get_name_to_search(self) -> str:
        """
            Возвращает имя для использования в поиске
        """
        raise NotImplemented


class TrackWrapper(TrackWrapperBase):

    def __init__(self, builder: TrackBuilder) -> None:
        self._track_id = builder.track_id
        self._albums = builder.albums
        self._artists = builder.artists
        self._title = builder.title
        self._uri = builder.uri
        self._duration_ms: int | None = builder.duration_ms
        self._available_for_listening: bool = builder.available_for_listening
        self._path = builder.path

    @property
    def id(self) -> int:
        return self._track_id

    @property
    def albums(self) -> typing.Tuple[AlbumWrapper]:
        return tuple(self._albums)

    @property
    def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        builder = YandexBuilderUrl()
        builder.set_track_id(self._track_id)

        if len(self._albums) == 0:
            logger.error("No albums found.")
            return builder.get_result()

        first_album_id = self._albums[0].id
        builder.set_album_id(first_album_id)
        return builder.get_result()

    @property
    def is_available(self) -> bool:
        return self._available_for_listening

    def get_filename(self) -> str | None:
        if os.path.exists(self._path):
            return self._path
        return None

    def duration(self) -> float:
        if self._duration_ms is not None:
            seconds, milliseconds = divmod(self._duration_ms, 1000)
            return seconds

        if not self.__contains_track_in_storage():
            logger.error(
                "Before determining the duration of a track, you need to set the track. Use try_download(_async)")
            return 0

        duration = get_duration_track(self._path)
        return duration

    def duration_str(self) -> str:
        duration_in_seconds = int(self.duration())
        minutes, seconds = divmod(duration_in_seconds, 60)
        return "{:02d}:{:02d}".format(minutes, seconds)

    def cover_url(self, size=1000) -> str | None:
        if self._uri is None:
            return None
        cover = self.__get_yandex_music_url()
        return cover

    def info(self, add_urls: bool) -> dict:
        albums = []
        artists = []

        if add_urls:
            builder_album = YandexBuilderUrl()
            builder_artist = YandexBuilderUrl()

            for album in self._albums:
                builder_album.set_album_id(album.id)

                album_title = f"[{album.title}]({builder_album.get_result()})"
                albums.append(album_title)

            for artist in self._artists:
                builder_artist.set_artist_id(artist.id)

                artist_title = f"[{artist.name}]({builder_artist.get_result()})"
                artists.append(artist_title)
        else:
            for album in self._albums:
                albums.append(album.title)

            for artist in self._artists:
                artists.append(artist.name)

        return {
            "title": self.title,
            "album": ','.join(albums),
            "artists": ','.join(artists)
        }

    def get_name_to_search(self) -> str:
        artists = ', '.join([artist.name for artist in self._artists])
        duration = self.duration_str()
        return f"🎵 {self._title} - {artists} [{duration}]"

    def __get_yandex_music_url(self, size=1000) -> str:
        url = self._uri
        url = url.replace("%%", '')
        url = f"https://{url}m{size}x{size}"
        return url

    def __contains_track_in_storage(self) -> bool:
        return check_existence_of_file(self._path)
