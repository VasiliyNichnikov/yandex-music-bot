import typing

from core.log_utils import get_logger
from storage.data import AnswerFromMusicService, PlaylistEntry, TrackData, AlbumData, PlaylistData, ShortAlbumData, \
    ShortArtistData
from storage.protocol import TracksStorageProtocol
from requests_to_music_service.protocol import RequestToServiceProtocol
from requests_to_music_service.protocol import ExecutingRequestsProtocol

logger = get_logger(__name__)


class Storage(TracksStorageProtocol):
    def __init__(self, executing: ExecutingRequestsProtocol) -> None:
        self._executing = executing
        self._data: typing.List[PlaylistEntry] = []
        self._last_id: int = 0

        self._uploaded_albums: typing.Dict[int, ShortAlbumData] = {}

    def get_loaded_playlists(self) -> typing.Tuple[PlaylistEntry, ...]:
        return tuple(self._data)

    def try_get_album_by_id(self, album_id: int) -> ShortAlbumData | None:
        if len(self._uploaded_albums) == 0:
            return None

        if album_id in self._uploaded_albums:
            return self._uploaded_albums[album_id]

        return None

    async def add(self, request: RequestToServiceProtocol) -> bool:
        data = await self._executing.processing(request)
        if data is None:
            return False

        if not isinstance(data, AnswerFromMusicService):
            logger.error("storage: incorrect data type returned.")
            return False

        if data.album is not None:
            album = data.album

            data_id = album.id
            data_title = album.title
            data_available = album.available
            tracks = album.tracks
            artists = album.artists

            entry = PlaylistEntry(self._last_id, data_id, data_title, data_available, tracks, artists)

            self._data.append(entry)
            self._last_id += 1

        if data.playlist is not None:
            playlist = data.playlist

            data_id = playlist.playlist_id
            data_title = playlist.title
            data_available = playlist.available
            tracks = playlist.tracks
            artists = []

            entry = PlaylistEntry(self._last_id, data_id, data_title, data_available, tracks, tuple(artists))

            self._data.append(entry)
            self._last_id += 1

        if data.artist is not None:
            artist = data.artist
            data_id = artist.id
            data_title = artist.name
            data_available = artist.available
            tracks = artist.tracks
            artists = [ShortArtistData(id=artist.id, name=artist.name)]

            entry = PlaylistEntry(self._last_id, data_id, data_title, data_available, tracks, tuple(artists))

            self._data.append(entry)
            self._last_id += 1

        for album in data.loaded_albums:
            if album.id in self._uploaded_albums:
                continue
            self._uploaded_albums[album.id] = album

        return True

    def get_tracks_range(self, min_value: int, max_value: int) -> typing.Tuple[TrackData]:
        tracks: typing.List[TrackData] = []

        for entry in self._data:
            tracks.extend(entry.tracks)

        if len(tracks) == 0:
            return tuple()

        if len(tracks) < max_value:
            max_value = len(tracks)

        if min_value < 0:
            min_value = 0

        if min_value == max_value:
            return tuple()

        group = tracks[min_value:max_value]
        return tuple(group)

    def clear(self) -> None:
        self._data.clear()
        self._uploaded_albums.clear()


