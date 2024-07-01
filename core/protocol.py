from typing import Protocol

from discord import VoiceClient

from requests_to_music_service.protocol import RequestToServiceProtocol


class PlayerProtocol(Protocol):

    def is_loop(self) -> bool:
        raise NotImplemented

    def is_running(self) -> bool:
        raise NotImplemented

    def is_paused(self) -> bool:
        raise NotImplemented

    async def preview_track(self) -> None:
        raise NotImplemented

    async def next_track(self, add_to_queue: bool = False) -> None:
        raise NotImplemented

    async def pause_track(self) -> None:
        raise NotImplemented

    async def stop_track(self, disconnect: bool, safely: bool = False) -> None:
        raise NotImplemented

    async def show_track_queue(self) -> None:
        raise NotImplemented

    def update_voice_client(self, voice_client: VoiceClient) -> None:
        raise NotImplemented

    async def add_track_request_and_play(self, request: RequestToServiceProtocol) -> None:
        raise NotImplemented

    async def change_loop(self, show_message: bool = True) -> None:
        raise NotImplemented
