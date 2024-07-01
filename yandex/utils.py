"""
    Дополнительные утиоитки
    Не очень нравиться все эти обертки, но пусть пока тут полежат
"""
import re
import typing

from core.log_utils import get_logger
from core.path_utils import check_existence_of_file, get_path_to_music
from storage.data import TrackData
from storage.protocol import TracksStorageProtocol
from yandex.track import TrackWrapperBase, AlbumBuilder, TrackBuilder, ArtistBuilder

logger = get_logger(__name__)


def get_track_wrapper(track: TrackData, storage: TracksStorageProtocol) -> TrackWrapperBase:
    builder = get_track_wrapper_builder(track, storage)
    return builder.build()


def get_track_wrapper_builder(track: TrackData, storage: TracksStorageProtocol) -> TrackBuilder:
    builder = TrackBuilder(track.id, track.title, duration_ms=track.duration_in_milliseconds)
    for album_id in track.album_ids:
        album = storage.try_get_album_by_id(album_id)
        if album is None:
            continue
        album_builder = AlbumBuilder(album.id, album.title, album.track_count)
        builder.add_album(album_builder.build())

    for artist in track.artists:
        artist_builder = ArtistBuilder(artist.id, artist.name)
        builder.add_artist(artist_builder.build())

    builder.set_cover_uri(track.cover_uri)
    builder.set_track_path(get_track_path(track))
    return builder


# Паттерн ссылки Яндекс.Музыка
pattern_yandex_body = "^https://music.yandex.[a-z]*/"


def is_yandex_music_url(url: str) -> bool:
    global pattern_yandex_body

    found_match_body = re.match(pattern_yandex_body, url)
    if found_match_body is None:
        return False
    if not url.startswith(found_match_body.group(0)):
        return False

    return True


def get_track_path(track: TrackData | TrackWrapperBase) -> str:
    name = get_name_track(track)
    return get_path_to_music(name)


def get_name_track(track: TrackData | TrackWrapperBase) -> str:
    track_id: int | None = None
    album_ids: typing.Tuple[int] = tuple()

    if isinstance(track, TrackWrapperBase):
        track_id = track.id
        album_ids = (album.id for album in track.albums) if len(track.albums) != 0 else tuple()

    if isinstance(track, TrackData):
        track_id = track.id
        album_ids = track.album_ids

    if album_ids is None or len(album_ids) == 0:
        logger.error("Albums not found.")
        return str(track_id)

    names = []
    for album_id in album_ids:
        names.append(f"{track_id}_{album_id}")

    for name in names:
        path = get_path_to_music(name)
        if check_existence_of_file(path):
            return name
    return names[0]
