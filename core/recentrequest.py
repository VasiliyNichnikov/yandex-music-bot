import dataclasses
import typing
from typing import Protocol
from datetime import datetime

from core.config import ConfigManager
from core.enumes import MusicCommandType, UrlType
from core.log_utils import get_logger


logger = get_logger(__name__)


@dataclasses.dataclass
class RecentRequestAdditionalData:
    user_name_playlist: str | None
    album_name_track: str | None


class RecentRequestProtocol(Protocol):

    @property
    def title(self) -> str:
        raise NotImplemented

    @property
    def command_type(self) -> MusicCommandType:
        raise NotImplemented

    @property
    def description(self) -> str:
        raise NotImplemented

    @property
    def date_time(self) -> datetime:
        raise NotImplemented

    @property
    def content(self) -> str | None:
        raise NotImplemented

    def get_description_for_button(self) -> str:
        raise NotImplemented


class OldRecentRequest(RecentRequestProtocol):
    def __init__(self,
                 config: ConfigManager,
                 command_type: MusicCommandType,
                 request: str | None,
                 date_time: datetime) -> None:
        messages = config["messages"]
        display_recommendations = {
            MusicCommandType.FAVORITE.value: {
                "title": messages["recommendation_favorite_title"],
                "description_with_button": messages["recommendation_favorite_description"],
                "description": messages["recommendation_favorite_description_default"]
            },
            MusicCommandType.URL.value: {
                "title": messages["recommendation_url_title"],
                "description_with_button": messages["recommendation_url_description"],
                "description": messages["recommendation_url_description_default"]
            },
            MusicCommandType.SEARCH.value: {
                "title": messages["recommendation_search_title"],
                "description_with_button": messages["recommendation_search_description"],
                "description": messages["recommendation_search_description_default"]
            },
            MusicCommandType.NOT_FOUND.value: {
                "title": messages["recommendation_not_found_title"],
                "description_with_button": messages["recommendation_not_found_description"],
                "description": messages["recommendation_not_found_description_default"]
            }
        }
        self._command_type = command_type
        self._selected_displaying_message = display_recommendations[command_type.value]
        self._request = request
        self._date_time = date_time
        self.name_button: str | None = None

    @property
    def title(self) -> str:
        return self._selected_displaying_message["title"]

    @property
    def command_type(self) -> MusicCommandType:
        return self._command_type

    @property
    def description(self) -> str:
        desc = self._selected_displaying_message["description"]
        if self._command_type == MusicCommandType.SEARCH:
            return desc.format(self._request)
        if self._command_type == MusicCommandType.URL:
            return desc.format(self._request)
        return desc.format()

    @property
    def content(self) -> str | None:
        return self._request

    @property
    def date_time(self) -> datetime:
        return self._date_time

    def get_description_for_button(self) -> str:
        desc = self._selected_displaying_message["description_with_button"]
        if self.name_button is None:
            logger.error("Name button is none.")
            self.name_button = "Empty"

        if self._command_type == MusicCommandType.SEARCH:
            return desc.format(self._request, self.name_button)
        if self._command_type == MusicCommandType.URL:
            return desc.format(self._request, self.name_button)
        return desc.format(self.name_button)


class PlayRecentRequest(RecentRequestProtocol):

    def __init__(self, config: ConfigManager, request_url: str, title: str, url_type: UrlType, additional_data: RecentRequestAdditionalData, date_time: datetime) -> None:
        messages = config["messages"]

        self._default_title = title
        self._title = self.__get_title(title, messages, url_type, additional_data)
        self._description: str = messages["recommendation_play_description_default"].format(title)
        self._description_body_with_button: str = messages["recommendation_play_description"]

        self._request_url = request_url
        self._date_time = date_time
        self.name_button: str | None = None

    @property
    def title(self) -> str:
        return self._title

    @property
    def command_type(self) -> MusicCommandType:
        return MusicCommandType.PLAY

    @property
    def description(self) -> str:
        return self._description

    @property
    def content(self) -> str | None:
        return self._request_url

    @property
    def date_time(self) -> datetime:
        return self._date_time

    def get_description_for_button(self) -> str:
        return self._description_body_with_button.format(self._default_title, self._request_url, self.name_button)

    @staticmethod
    def __get_title(title: str, messages: typing.Dict[str, str], url_type: UrlType, additional_data: RecentRequestAdditionalData) -> str:
        match url_type:
            case UrlType.IS_ALBUM:
                return messages["recommendation_play_album_title"].format(title)
            case UrlType.IS_PLAYLIST:
                if additional_data.user_name_playlist is not None:
                    return messages["recommendation_play_playlist_with_user_title"].format(title, additional_data.user_name_playlist)
                return messages["recommendation_play_playlist_title"].format(title)
            case UrlType.IS_ARTIST:
                return messages["recommendation_play_artist_title"].format(title)
            case UrlType.IS_ONE_TRACK:
                if additional_data.album_name_track is not None:
                    return messages["recommendation_play_track_from_album_title"].format(title, additional_data.album_name_track)
                return messages["recommendation_play_track_title"].format(title)

        logger.error(f"Title for type {url_type} not found.")
        return messages["recommendation_not_found_title"]
