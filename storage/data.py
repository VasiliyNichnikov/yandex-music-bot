import dataclasses
import typing


@dataclasses.dataclass
class ShortArtistData:
    id: int
    name: str


@dataclasses.dataclass
class TrackData:
    id: int
    title: str
    available: bool
    duration_in_milliseconds: int
    cover_uri: str
    artists: typing.Tuple[ShortArtistData, ...]
    album_ids: typing.Tuple[int, ...]


@dataclasses.dataclass
class AlbumData:
    id: int
    title: str
    available: bool
    cover_uri: str
    track_count: int
    artists: typing.Tuple[ShortArtistData, ...]
    tracks: typing.Tuple[TrackData, ...]


@dataclasses.dataclass
class ArtistData:
    id: int
    name: str
    cover_uri: str | None
    available: bool
    tracks: typing.Tuple[TrackData, ...]


@dataclasses.dataclass
class ShortAlbumData:
    id: int
    title: str
    available: bool
    cover_uri: str | None
    track_count: int
    artists: typing.Tuple[ArtistData, ...]


@dataclasses.dataclass
class PlaylistData:
    owner_id: int
    user_login: str
    user_name: str
    playlist_id: int
    title: str
    available: bool
    cover_uri: str | None
    tracks: typing.Tuple[TrackData, ...]


@dataclasses.dataclass
class AnswerFromMusicService:
    playlist: PlaylistData | None
    album: AlbumData | None
    artist: ArtistData | None

    loaded_albums: typing.Tuple[ShortAlbumData]  # Все загруженные альбомы без информации о треках


@dataclasses.dataclass
class PlaylistEntry:
    """
        Отличается от обычного плейлиста, в том
        что playlistEntry может состаять из альбома или плейлиста
    """
    id: int
    data_id: int
    title: str                             # Название альбома или плейлиста
    number_tracks: int                     # Кол-во всех треков
    tracks: typing.Tuple[TrackData, ...]   # Все треки
    artists: typing.Tuple[ShortArtistData, ...]  # Все артисыт