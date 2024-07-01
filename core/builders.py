import typing

from discord import Embed

from core._color_data import DISCORD_COLORS
from core.config import ConfigManager
from core.recentrequest import OldRecentRequest


class YandexBuilderUrl:
    def __init__(self) -> None:
        self._body = "https://music.yandex.ru"
        self._album_str = "album"
        self._track_str = "track"
        self._artist_str = "artist"
        self._users_str = "users"
        self._playlist_str = "playlists"

        self._album_id = None
        self._track_id = None
        self._artist_id = None
        self._user_login = None
        self._playlist_id = None

    def set_album_id(self, album_id: int) -> None:
        self._album_id = album_id

    def set_track_id(self, track_id: int) -> None:
        self._track_id = track_id

    def set_artist_id(self, artist_id: int) -> None:
        self._artist_id = artist_id

    def set_playlist_id(self, user_login: str, playlist_id: int) -> None:
        self._user_login = user_login
        self._playlist_id = playlist_id

    def get_result(self) -> str:
        result = [self._body]
        if self._album_id is not None:
            result.append(self._album_str)
            result.append(str(self._album_id))
        if self._track_id is not None:
            result.append(self._track_str)
            result.append(str(self._track_id))
        if self._artist_id is not None:
            result.append(self._artist_str)
            result.append(str(self._artist_id))
        if self._playlist_id is not None and self._user_login is not None:
            result.append(self._users_str)
            result.append(str(self._user_login))
            result.append(self._playlist_str)
            result.append(str(self._playlist_id))

        return '/'.join(result)


class CoverTrackBuilder:
    def __init__(self, config: ConfigManager) -> None:
        self._title = config["messages"]["default_description_title"]
        self._description = config["messages"]["default_description"]
        self._orange = DISCORD_COLORS["orange"]
        self._icon = config["default_icon_url_vk"]
        self._content = config["message_content_name"]
        self._recommendation_requests: typing.List[OldRecentRequest] = []
        self._duration: str | None = None

    def change_icon(self, url: str) -> "CoverTrackBuilder":
        self._icon = url
        return self

    def change_title(self, title: str) -> "CoverTrackBuilder":
        self._title = title
        return self

    def change_description(self, description: str) -> "CoverTrackBuilder":
        self._description = description
        return self

    def add_recommendation_request(self, request: OldRecentRequest) -> "CoverTrackBuilder":
        if request in self._recommendation_requests:
            return self
        self._recommendation_requests.append(request)

    def add_duration(self, duration: str) -> "CoverTrackBuilder":
        self._duration = duration
        return self

    def get_embed(self) -> Embed:
        if len(self._recommendation_requests) == 0:
            return self.__get_embed_with_track()
        return self.__get_embed_with_recent_requests()

    def __get_embed_with_track(self) -> Embed:
        title = self._title if self._duration is None else f"{self._title} - [{self._duration}]"
        embed = Embed(title=title, description=self._description, colour=self._orange)
        embed.set_thumbnail(url=self._icon)

        return embed

    def __get_embed_with_recent_requests(self) -> Embed:
        embed: Embed = Embed(title=self._title,
                             description=self._description,
                             colour=self._orange)
        for request in self._recommendation_requests:
            embed.add_field(name=request.title, value=request.get_description_for_button(), inline=False)
            embed.set_thumbnail(url=self._icon)
        return embed
