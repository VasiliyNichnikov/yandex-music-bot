"""
    Данные которые мы отдаем наружу
    Так как с сессией работаем только внутри ClientDataBaseAPI
"""
import dataclasses
import datetime
import typing


@dataclasses.dataclass
class RequestsToMusicData:
    name_command: str
    url: str
    date_time: datetime.datetime
    guild_id: int
    title: str
    is_album: bool
    is_playlist: bool
    is_artist: bool
    is_track: bool
    user_name_playlist: str | None  # Какой пользователь содержит этот плейлист
    album_name_track: str | None    # Какай альбом содержит трек


@dataclasses.dataclass
class GuildData:
    guild_id: int
    text_channel_id: int
    thread_id: int
    requests_to_music: typing.List[RequestsToMusicData]
