import asyncio

from requests_to_music_service.protocol import ExecutingRequestsProtocol, RequestToServiceProtocol, \
    RequestToInstallTrack
from storage.data import AnswerFromMusicService
from core.log_utils import get_logger


logger = get_logger(__name__)


class ExecutingRequests(ExecutingRequestsProtocol):

    def __init__(self, number_of_attempts: int, delay_between_errors: float) -> None:
        """
            Выполняем запрос, обрабатывая ошибки
        :param number_of_attempts: Количество попыток в случае ошибки
        :param delay_between_errors: Время задержки в случае ошибки
        """
        self._number_of_attempts: int = number_of_attempts
        self._delay_between_errors: float = delay_between_errors

    async def processing(self, request: RequestToServiceProtocol) -> AnswerFromMusicService | None:
        if request.is_loaded:
            return request.get_loaded_data()

        await self.__try_load_data(request)

        if request.is_loaded:
            return request.get_loaded_data()

        return None

    async def processing_track(self, request: RequestToInstallTrack) -> bool:
        if request.is_loaded:
            return True

        await self.__try_load_data(request)

        return request.is_loaded

    async def __try_load_data(self, request: RequestToServiceProtocol | RequestToInstallTrack) -> None:
        attempt = 0

        while attempt < self._number_of_attempts:
            try:
                state = await request.perform()
                if state:
                    break
                else:
                    await asyncio.sleep(self._delay_between_errors)
            except Exception as e:
                logger.warning(f"processing track: error {e} during request processing.")
                await asyncio.sleep(self._delay_between_errors)
            finally:
                attempt += 1

