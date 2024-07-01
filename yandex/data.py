import dataclasses
import typing

from yandex_music import Artist, Album, Playlist, Track

from core.enumes import MusicCommandType


@dataclasses.dataclass
class YandexMusicRequestData:
    command_type: MusicCommandType

    artist: Artist | None
    album: Album | None
    playlist: Playlist | None
    track: Track | None
    search_tracks: typing.Tuple[Track, ...] | None
