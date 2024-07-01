from typing import Protocol

from requests_to_music_service.data import InfoAboutRequest
from storage.data import AnswerFromMusicService


class RequestToServiceProtocol(Protocol):

    @property
    def is_loaded(self) -> bool:
        raise NotImplemented

    def try_get_info_about_request(self) -> InfoAboutRequest | None:
        """
            Пытаемся преобразовать запрос в Url в зависимости от того какие данные пришли
        """
        raise NotImplemented

    def get_loaded_data(self) -> AnswerFromMusicService | None:
        raise NotImplemented

    async def perform(self) -> bool:
        raise NotImplemented


class RequestToInstallTrack(Protocol):
    @property
    def is_loaded(self) -> bool:
        """
            TODO:
            нужно доработать для ОЗУ
        :return:
        """
        raise NotImplemented

    async def perform(self) -> bool:
        raise NotImplemented


class ExecutingRequestsProtocol(Protocol):

    async def processing(self, request: RequestToServiceProtocol) -> AnswerFromMusicService | None:
        raise NotImplemented

    async def processing_track(self, request: RequestToInstallTrack) -> bool:
        raise NotImplemented
