"""
    Содержит код для проигрывания треков
"""

import typing

from discord import FFmpegPCMAudio, VoiceClient

from core.log_utils import get_logger
from core.timer import Timer
from utils.taskmanager.protocols import TaskManagerProtocol
from yandex.collector import TrackQueue
from yandex.track import TrackWrapperBase

logger = get_logger(__name__)


class Player:
    def __init__(self, queue: TrackQueue, task_manager: TaskManagerProtocol) -> None:
        self._voice_client: None | VoiceClient = None
        self._selected_track: TrackWrapperBase | None = None
        self._played_tracks: typing.List[TrackWrapperBase] = []
        self._queue: TrackQueue = queue
        self._is_loop_tracks: bool = False

        # Делегаты
        # Вызывается при старте трека
        self._on_track_started_action: typing.Callable[[TrackWrapperBase], None] | None = None
        # Вызывается после завершения проигрывания трека
        self._on_track_completed_action: typing.Callable[[TrackWrapperBase], None] | None = None
        self._task_manager: TaskManagerProtocol = task_manager
        self._timer_for_turning_on_next_track: Timer | None = None
        # Оставшиеся время трека, когда он находится на таймере
        self._remaining_time_of_track_on_pause: int | None = None

    @property
    def selected_track(self) -> TrackWrapperBase | None:
        return self._selected_track

    @property
    def is_running(self) -> bool:
        return self._selected_track is not None

    @property
    def is_playing(self) -> bool:
        if not self.__check_voice_client_and_log_errors():
            return False
        return self._voice_client.is_playing()

    @property
    def is_loop_track(self) -> bool:
        return self._is_loop_tracks

    @property
    def is_paused(self) -> bool:
        if not self.__check_voice_client_and_log_errors():
            return False
        return self._voice_client.is_paused()

    @property
    def is_played_tracks_empty(self) -> bool:
        return len(self._played_tracks) == 0

    def update_voice_client(self, voice_client: VoiceClient) -> None:
        self._voice_client = voice_client

    def change_loop(self) -> None:
        self._is_loop_tracks = not self._is_loop_tracks
        logger.debug(f"Is loop tracks: {self._is_loop_tracks}")

    def play_current_track(self) -> None:
        self.__try_play_current_track()

    def set_next_track(self, automatic_transition: bool = False) -> None:
        self.__try_stop_voice_client()

        if automatic_transition and self._is_loop_tracks:
            return

        if self._selected_track is not None:
            self._played_tracks.insert(0, self._selected_track)

        self._selected_track = self._queue.get_next_track()

    def set_preview_track(self) -> None:
        self.__try_stop_voice_client()

        if self._selected_track is not None:
            self._queue.add_track_first_to_queue(self._selected_track)
        self._selected_track = self.__get_preview_track()

    def pause(self) -> None:
        if not self.__check_voice_client_and_log_errors():
            return

        if self._selected_track is None:
            return

        if self._voice_client.is_playing():
            if self._timer_for_turning_on_next_track is None:
                logger.error("(Pause) Timer for turning on next track is None.")
            else:
                self._remaining_time_of_track_on_pause = self._timer_for_turning_on_next_track.remaining_time
                self._timer_for_turning_on_next_track.stop()
                self._timer_for_turning_on_next_track = None

            logger.info(f"Track {self._selected_track.title} on pause.")
            self._voice_client.pause()

    def resume(self) -> None:
        if not self.__check_voice_client_and_log_errors():
            return

        if self._selected_track is None:
            return

        if self._voice_client.is_paused():
            if self._remaining_time_of_track_on_pause is None:
                logger.error("Remaining time of track on pause is None.")
            elif self._timer_for_turning_on_next_track is not None:
                logger.error("Timer for turning on next track is not None.")
            else:
                self._timer_for_turning_on_next_track = self.__create_timer(self._remaining_time_of_track_on_pause)
                self._timer_for_turning_on_next_track.start()

            logger.info(f"Track {self._selected_track.title} restored from a pause.")
            self._voice_client.resume()

    def stop(self, safely: bool = True) -> None:
        if safely and not self.__check_voice_client_and_log_errors():
            return

        self.__try_stop_voice_client()
        self._selected_track = None
        self._played_tracks.clear()
        self._is_loop_tracks = False
        if self._timer_for_turning_on_next_track is not None:
            self._timer_for_turning_on_next_track.stop()
            self._timer_for_turning_on_next_track = None

    def set_track_started_action(self, action: typing.Callable[[TrackWrapperBase], None]) -> None:
        if self._on_track_started_action is not None:
            logger.warning("on_track_started_action is not none.")
        self._on_track_started_action = action

    def set_track_completed_action(self, action: typing.Callable[[TrackWrapperBase], None]) -> None:
        if self._on_track_completed_action is not None:
            logger.warning("on_track_completed_action is not none.")
        self._on_track_completed_action = action

    def __check_voice_client_and_log_errors(self, safe=False) -> bool:
        if self._voice_client is None:
            if not safe:
                logger.error("Voice client is None.")
            return False

        if not self._voice_client.is_connected():
            if not safe:
                logger.error("Check voice client: Voice client is not connected.")
            return False
        return True

    def __try_play_current_track(self) -> None:
        """
            Пытаемся проиграть текущий трек
            Если плеер не занят другим треком
        """
        if self._selected_track is not None:
            self._queue.update_queue(None)
            self.__play_current_track()
            return

        if not self._queue.is_empty:
            self._queue.update_queue(self.__set_next_track_and_play)
            return

        if self._selected_track is None:
            self.__try_stop_voice_client()

    def __set_next_track_and_play(self) -> None:
        self.set_next_track()
        self.__try_play_current_track()

    def __play_current_track(self) -> None:
        if self._selected_track is None:
            logger.error("Selected track is None.")
            return

        if self._voice_client is None:
            logger.error("Voice client is None.")
            return

        if not self._voice_client.is_connected():
            logger.error("Play current track: Voice client is not connected.")
            return

        if self._voice_client.is_playing():
            logger.error("The track is already playing.")
            return

        duration = self._selected_track.duration()
        logger.info(f"Start playing track. Title: {self._selected_track.title}; Duration: {duration}.")

        self.__play_from_hard_drive(self._selected_track)
        if self._on_track_started_action is not None:
            self._on_track_started_action(self._selected_track)

    def __play_from_hard_drive(self, track: TrackWrapperBase) -> None:
        filename = track.get_filename()
        if filename is None:
            logger.error("Filename is None.")
            return

        if self._timer_for_turning_on_next_track is not None:
            self._timer_for_turning_on_next_track.stop()
            self._timer_for_turning_on_next_track = None

        duration = track.duration()
        self._timer_for_turning_on_next_track = self.__create_timer(duration)

        ffmpeg = FFmpegPCMAudio(source=filename)
        self._voice_client.play(source=ffmpeg)
        self._timer_for_turning_on_next_track.start()

    def __play_next_track_automatic(self) -> None:
        if self._timer_for_turning_on_next_track is None:
            logger.error("timer is none.")
        else:
            self._timer_for_turning_on_next_track.stop()
            self._timer_for_turning_on_next_track = None

        if self._on_track_completed_action is not None:
            self._on_track_completed_action(self._selected_track)

        self.set_next_track(automatic_transition=True)
        self.play_current_track()

    def __try_stop_voice_client(self) -> None:
        if not self.__check_voice_client_and_log_errors():
            return

        if self._voice_client.is_playing():
            self._voice_client.stop()

    def __get_preview_track(self) -> TrackWrapperBase | None:
        if len(self._played_tracks) > 0:
            first = self._played_tracks.pop(0)
            return first
        return None

    def __create_timer(self, waiting_time: int | float) -> Timer:
        timer = Timer(waiting_time, self._task_manager)
        timer.set_invoke(self.__play_next_track_automatic)
        return timer
