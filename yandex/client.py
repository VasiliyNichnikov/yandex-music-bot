import typing
from abc import ABC, abstractmethod

from yandex_music import ClientAsync, Track

from core.log_utils import get_logger
from core.config import ConfigManager
from requests_to_music_service.executing_requests import ExecutingRequests
from requests_to_music_service.protocol import RequestToServiceProtocol, ExecutingRequestsProtocol, \
    RequestToInstallTrack
from storage.data import TrackData
from requests_to_music_service.yandex_music import RequestToYandexMusicService, RequestToInstallYandexTrack
from yandex.requests import RequestBuilder
from yandex.protocol import TracksLoaderProtocol
from yandex.utils import is_yandex_music_url
from yandex.utils import get_track_path

logger = get_logger(__name__)


class YandexMusicBase(ABC):
    @abstractmethod
    async def init(self) -> None:
        raise NotImplemented

    @abstractmethod
    def get_request_by_url(self, url: str) -> RequestToServiceProtocol:
        raise NotImplemented

    @abstractmethod
    def get_request_from_favorite(self, index: int) -> RequestToServiceProtocol:
        raise NotImplemented

    @abstractmethod
    def get_request_by_search(self, search: str, max_tracks: int) -> RequestToServiceProtocol:
        raise NotImplemented

    @abstractmethod
    def get_automatic_request(self, request: str, max_tracks: int) -> RequestToServiceProtocol:
        raise NotImplemented


class YandexMusicAccount(YandexMusicBase, TracksLoaderProtocol):

    def __init__(self, config: ConfigManager) -> None:
        self._max_tracks_in_list = config["max_tracks_in_list"]
        self._client = ClientAsync(token=config["yandex_token"])
        self._config = config
        self._executing_requests: ExecutingRequestsProtocol = ExecutingRequests(self._config["number_of_attempts_when_requesting_music_service"],
                                                                                self._config["delay_in_case_of_error_when_requesting_music_service"])

    async def init(self) -> None:
        await self._client.init()

    async def upload_track_to_RAM(self, track: TrackData) -> bool:
        state = await self.__download_tracks([track], True, None)
        return state

    async def upload_track_to_hard_drive(self, track: TrackData) -> bool:
        state = await self.__download_tracks([track], False)
        return state

    def get_request_by_url(self, url: str) -> RequestToServiceProtocol:
        ym_request = RequestBuilder(self._config).set_url(url).get_result(self._client)
        return RequestToYandexMusicService(ym_request)

    def get_request_from_favorite(self, index: int) -> RequestToServiceProtocol:
        ym_request = RequestBuilder(self._config).set_is_favorite().get_result(self._client)
        return RequestToYandexMusicService(ym_request)

    def get_request_by_search(self, search: str, max_tracks: int) -> RequestToServiceProtocol:
        ym_request = RequestBuilder(self._config).set_search(search).set_max_tracks(max_tracks)
        result = ym_request.get_result(self._client)
        return RequestToYandexMusicService(result)

    def get_automatic_request(self, request: str, max_tracks: int) -> RequestToServiceProtocol:
        """
            Автоматически определяет какой запрос вернуть
            Если запрос является ссылкой, вернется запрос по ссылке
            Если запрос является обычным поиском, запрос по поиску
        """
        ym_request = RequestBuilder(self._config).set_max_tracks(max_tracks)
        if is_yandex_music_url(request):
            ym_request.set_url(request)
        else:
            ym_request.set_search(request)

        result = ym_request.get_result(self._client)
        return RequestToYandexMusicService(result)

    async def __download_tracks(self, tracks_data: typing.List[TrackData], ram: bool) -> bool:
        track_ids = [track.id for track in tracks_data]
        tracks_ym: typing.List[Track] = await self._client.tracks(track_ids=track_ids)
        track_requests: typing.List[RequestToInstallTrack] = []
        for i in range(len(tracks_data)):
            track_ym = tracks_ym[i]
            track_data = tracks_data[i]
            path = get_track_path(track_data)
            track_request = RequestToInstallYandexTrack(track_ym, ram, path)
            track_requests.append(track_request)

        number_of_tracks_uploaded = 0

        for request in track_requests:
            state = await self._executing_requests.processing_track(request)
            if state:
                number_of_tracks_uploaded += 1

        return number_of_tracks_uploaded == len(tracks_data)
