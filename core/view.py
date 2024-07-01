"""
    Отвечает за отображение данных
    Очень страшно
"""
import typing

import discord
from discord import Interaction, TextChannel, Thread
from discord.ui import View, Button

from core.builders import CoverTrackBuilder
from core.factories import BotFactory
from core.log_utils import get_logger
from core.protocol import PlayerProtocol
from core.recentrequest import OldRecentRequest
from permissions.discord_view_helper import check_permissions_view
from utils.blocker import BlockerSupported, Blocker, check_lock
from yandex.track import TrackWrapperBase
from core._color_data import DISCORD_COLORS

logger = get_logger(__name__)


class CoverTrackView(View):
    def __init__(self, player: PlayerProtocol) -> None:
        self._player: PlayerProtocol = player
        super().__init__(timeout=None)

        # Динамические кнопки
        self._loop_button: Button | None = None

        self.__add_loop_button()

    @discord.ui.button(style=discord.ButtonStyle.green, emoji="⏮️")
    async def __previous_track_button(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self._player.preview_track()

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="⏸️")
    async def __pause_track_button(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await self._player.pause_track()
        button.style = discord.ButtonStyle.blurple if self._player.is_paused() else discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.green, emoji="⏭️")
    async def __next_track_button(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self._player.next_track()

    @discord.ui.button(style=discord.ButtonStyle.red, emoji="⏹️")
    async def __stop_track_button(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self._player.stop_track(disconnect=False)

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Очередь треков", emoji="📋", row=2)
    async def __show_track_queue(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self._player.show_track_queue()

    def __add_loop_button(self) -> None:
        if self._loop_button is not None:
            return

        style = discord.ButtonStyle.primary if self._player.is_loop() else discord.ButtonStyle.gray
        self._loop_button = Button(
            style=style,
            label="Повтор трека",
            emoji="➿",
            row=2
        )
        self._loop_button.callback = self.__set_loop_track_callback
        self.add_item(self._loop_button)

    async def __set_loop_track_callback(self, interaction: Interaction) -> None:
        if self._loop_button is None:
            logger.error("loop button is None.")
            return

        await self._player.change_loop(show_message=False)
        self._loop_button.style = discord.ButtonStyle.primary if self._player.is_loop() else discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self)


class RecentlyListenedTracksView:
    def __init__(self, try_search_and_complet_command: typing.Callable[[str, str, discord.Message], typing.Awaitable[None]]) -> None:
        self._recently_requests: typing.List[OldRecentRequest] = []
        self._try_search_and_complete_command = try_search_and_complet_command

    def add_recently_request(self, request: OldRecentRequest) -> None:
        if request in self._recently_requests:
            return

        self._recently_requests.append(request)

    def create_view(self) -> discord.ui.View:
        view = discord.ui.View(timeout=None)

        number_button = 1
        for request in self._recently_requests:
            request.name_button = f"Включить: {number_button}"
            button = discord.ui.Button(style=discord.ButtonStyle.green, label=request.name_button, emoji="💽")
            button.callback = lambda interaction, request_copy=request: self.__on_click_button_handler(interaction, request_copy)
            view.add_item(button)
            number_button += 1
        return view

    async def __on_click_button_handler(self, interaction: Interaction, request: OldRecentRequest) -> None:
        await interaction.response.defer()
        # Самый страшный костыль страшный))))
        # Но если не поменять автора, бот не найдет гс пользователя и как следствие не выполнит команду
        # Так же меняем и контент. Так скажем костыли чтобы не писать кодус)
        # Работает только для команд через PREFIX
        interaction.message.author = interaction.user
        if request.content is not None:
            interaction.message.content = request.content
        await self._try_search_and_complete_command("music", request.command_type.value, interaction.message)


class DiscordViewHelper(BlockerSupported):
    def __init__(self, thread: "UserThread", factory: BotFactory) -> None:
        self._factory = factory
        self._thread: "UserThread" = thread
        self._on_thread_created_invoke: typing.Callable[[int], None] | None = None
        self._on_text_chanel_created_invoke: typing.Callable[[int], None] | None = None
        self._message_with_recommendation: discord.Message | None = None

        # Текущие id текстового канала и ветки с историей
        self.__text_channel_id: int | None = None
        self.__history_thread_id: int | None = None

        # Блокируем все команды сразу
        self._blocker = Blocker()
        self._blocker.block()

    @property
    def is_blocked(self) -> bool:
        return self._blocker.is_blocked()

    def set_on_thread_created(self, on_thread_channel_created: typing.Callable[[int], None]) -> None:
        self._on_thread_created_invoke = on_thread_channel_created

    def set_on_text_chanel_invoke(self, on_text_channel_created: typing.Callable[[int], None]) -> None:
        self._on_text_chanel_created_invoke = on_text_channel_created

    @property
    def _text_channel_id(self) -> int | None:
        return self.__text_channel_id

    @_text_channel_id.setter
    def _text_channel_id(self, value: int) -> None:
        if self.__text_channel_id != value:
            self.__text_channel_id = value
            self.__try_invoke(self._on_text_chanel_created_invoke, value)

    @property
    def _history_thread_id(self) -> int | None:
        return self.__history_thread_id

    @_history_thread_id.setter
    def _history_thread_id(self, value: int) -> None:
        if self.__history_thread_id != value:
            self.__history_thread_id = value
            self.__try_invoke(self._on_thread_created_invoke, value)

    @property
    async def _text_channel(self) -> discord.TextChannel:
        return await self.__get_or_create_text_channel_with_music()

    @property
    async def _history_thread(self) -> discord.Thread:
        text_channel = await self._text_channel
        return await self.__get_or_create_history_thread(text_channel)

    @property
    def is_initialized(self) -> bool:
        return not self._blocker.is_blocked()

    def is_text_channel_with_music(self, text_channel_id: int) -> bool:
        return self.__text_channel_id is not None and self.__text_channel_id == text_channel_id

    @check_permissions_view
    async def init_text_channel_and_history_thread(self, text_channel_id: int | None,
                                                   history_thread_id: int | None) -> None:
        """
            Тут порядок важен.
            Сначала инитим id-s после чего текстовый канал и ветку
        """
        default_text_channel = self.__get_text_channel_with_default_name()
        default_text_channel_id = default_text_channel.id if default_text_channel is not None else None

        default_thread_history = self.__get_thread_history_with_default_name(default_text_channel)
        default_thread_history_id = default_thread_history.id if default_thread_history is not None else None

        if default_text_channel_id is None or (default_text_channel_id is not None and default_text_channel_id == text_channel_id):
            self.__text_channel_id = text_channel_id
        else:
            # Значит у нас уже есть канал с музыкой и нам нужно только обновить базу данных
            self._text_channel_id = default_text_channel_id

        if default_thread_history_id is None or (default_thread_history_id is not None and default_thread_history_id == history_thread_id):
            self.__history_thread_id = history_thread_id
        else:
            # Значит у нас уже есть ветка и нам нужно только обновить базу данных
            self._history_thread_id = default_thread_history_id

        await self._text_channel
        await self._history_thread
        self._blocker.unlock()

    @check_lock
    async def add_track_to_history(self, track: TrackWrapperBase) -> None:
        builder = self.__get_cover_build_to_selected_track(track)
        embed = builder.get_embed()
        history_thread = await self._history_thread
        await history_thread.send(embed=embed)

    @check_lock
    async def update_cover_for_selected_track(self, track: TrackWrapperBase) -> None:
        builder = self.__get_cover_build_to_selected_track(track)
        await self.__update_cover(builder, view=CoverTrackView(self._thread.player))

    @check_lock
    async def update_cover_to_default(self) -> None:
        builder = CoverTrackBuilder(self._thread.config)
        recent_requests = self._thread.get_recent_requests()

        show_recent_requests: bool = len(recent_requests) != 0
        buttons: None | discord.ui.View = None
        if show_recent_requests:
            recent_listened_track_buttons = self._factory.create_recent_listened_tracks_view()
            for recent_request in recent_requests:
                builder.add_recommendation_request(recent_request)
                recent_listened_track_buttons.add_recently_request(recent_request)

            command_id = self._thread.slash_commands["play"]
            message = str.format(self._thread.config["messages"]["description_with_recent_requests"],
                                 command_id=command_id)
            builder.change_description(message)
            buttons = recent_listened_track_buttons.create_view()
        else:
            # Лайфхак, чтобы добавить id команды и не лесть в билдер
            command_id = self._thread.slash_commands["play"]
            message = str.format(self._thread.config["messages"]["default_description"],
                                 command_id=command_id)
            builder.change_description(message)

        await self.__update_cover(builder, view=buttons)

    @check_lock
    async def show_track_queue(self, next_tracks: typing.Tuple[TrackWrapperBase, ...]) -> None:
        messages = self._thread.config["messages"]
        max_tracks_count = self._thread.config["maximum_display_of_tracks_in_queue"]

        limited_quantity_tracks = next_tracks[:max_tracks_count]

        description = messages["track_queue_description"].format(len(next_tracks))
        embed = discord.Embed(title=messages["track_queue_title"],
                              description=description,
                              color=DISCORD_COLORS["orange"])

        number = 1
        if len(limited_quantity_tracks) != 0:
            for track in limited_quantity_tracks:
                if number == 25:
                    break

                info_about_track = track.info(add_urls=False)
                title = info_about_track["title"]
                artists = info_about_track["artists"]

                embed.add_field(name=f"{number}) {title} - {artists}",
                                value=f"{messages['duration']}: {track.duration_str()}",
                                inline=False)
                number += 1

        text_channel: discord.TextChannel = await self._text_channel
        await self._thread.message_manager.send_message_text_channel(text_channel=text_channel, embed=embed)

    @check_lock
    async def show_enable_loop(self) -> None:
        message = self._thread.config["messages"]["enable_loop"]
        text_channel: discord.TextChannel = await self._text_channel
        await self._thread.message_manager.send_message_text_channel(text_channel=text_channel, content=message)

    @check_lock
    async def show_disable_loop(self) -> None:
        message = self._thread.config["messages"]["disable_loop"]
        text_channel: discord.TextChannel = await self._text_channel
        await self._thread.message_manager.send_message_text_channel(text_channel=text_channel, content=message)

    @check_lock
    async def check_existence_of_text_channel_and_thread(self) -> None:
        await self._text_channel
        await self._history_thread

    @check_lock
    async def send_message_not_tracks_in_queue(self) -> None:
        message = self._thread.config["messages"]["not_tracks_in_queue"]
        await self.__send_message(text=message)

    @check_lock
    async def send_message_not_tracks_in_previous(self) -> None:
        message = self._thread.config["messages"]["not_tracks_in_previous"]
        await self.__send_message(text=message)

    async def __send_message(self, text: str) -> None:
        text_channel: discord.TextChannel = await self._text_channel
        await self._thread.message_manager.send_message_text_channel(text_channel=text_channel, content=text)

    def __get_cover_build_to_selected_track(self, track: TrackWrapperBase) -> CoverTrackBuilder:
        info = track.info(add_urls=True)

        url = track.cover_url()
        title = info["title"]
        album = info["album"]
        artists = info["artists"]

        description = f"**Альбом:** {album}\n**Артист(ы):** {artists}"

        builder = CoverTrackBuilder(self._thread.config)
        if url is not None:
            builder.change_icon(url)

        if title is not None:
            builder.change_title(title)

        if description is not None:
            builder.change_description(description)

        track_duration = track.duration_str()
        builder.add_duration(track_duration)
        return builder

    async def __update_cover(self, cover_builder: CoverTrackBuilder, view: discord.ui.View = None) -> None:
        await self.__try_delete_recommendation_message()
        content = self._thread.config["message_content_name"]

        cover_message = await self.__get_message_with_cover(content)

        embed = cover_builder.get_embed()

        if cover_message is None:
            text_channel = await self._text_channel
            await text_channel.send(content=content, file=None, view=view, embed=embed)
            return
        await cover_message.edit(content=content, embed=embed, view=view)

    async def __get_message_with_cover(self, content: str) -> None | discord.Message:
        text_channel = await self._text_channel
        if text_channel is None:
            logger.critical("Text channel with music is None")
            return None

        messages = [message async for message in text_channel.history(limit=200)]
        if len(messages) == 0:
            return None

        desired_message: discord.Message | None = None
        for message in messages:
            if message.author.bot and message.content.lower() == content.lower():
                desired_message = message
            else:
                await self._thread.message_manager.delete(message)
        return desired_message

    async def __get_or_create_text_channel_with_music(self) -> TextChannel:
        if self._text_channel_id is None:
            text_channel = await self.__create_default_text_channel()
            self._text_channel_id = text_channel.id
            return text_channel

        current_text_channel: typing.Tuple[TextChannel] = tuple(filter(
            lambda channel: channel.id == self._text_channel_id,
            self._thread.guild.text_channels))

        if len(current_text_channel) != 1:
            text_channel = await self.__create_default_text_channel()
            logger.info(f"Text channel with the id {self._text_channel_id} from the database was not found. Update text channel id to {text_channel.id}")
            self._text_channel_id = text_channel.id
            return text_channel

        return current_text_channel[0]

    async def __get_or_create_history_thread(self, text_channel: TextChannel) -> Thread:
        if self._history_thread_id is None:
            thread = await self.__create_default_history_thread(text_channel)
            self._history_thread_id = thread.id
            return thread

        current_thread: typing.Tuple[Thread] = tuple(filter(
            lambda t: t.id == self._history_thread_id, text_channel.threads))
        if len(current_thread) != 1:
            thread = await self.__create_default_history_thread(text_channel)
            logger.info(f"Thread with the id {self._history_thread_id} from the database was not found. Update thread id to {thread.id}.")
            self._history_thread_id = thread.id
            return thread

        return current_thread[0]

    async def __create_default_text_channel(self) -> TextChannel:
        return await self._thread.guild.create_text_channel(name=self._thread.config["channel_with_music_default_name"],
                                                            topic=self._thread.config["messages"]["text_channel_music_topic"])

    async def __create_default_history_thread(self, text_channel: TextChannel) -> Thread:
        return await text_channel.create_thread(name=self._thread.config["history_thread_default_name"],
                                                type=discord.ChannelType.public_thread)

    async def __try_delete_recommendation_message(self) -> None:
        if self._message_with_recommendation is not None:
            await self._thread.message_manager.delete(self._message_with_recommendation)
            self._message_with_recommendation = None

    def __get_text_channel_with_default_name(self) -> TextChannel | None:
        default_text_channel: typing.Tuple[TextChannel] = tuple(filter(
            lambda channel: channel.name == self._thread.config["channel_with_music_default_name"].lower(),
            self._thread.guild.text_channels))

        if default_text_channel is None or len(default_text_channel) == 0:
            return None
        return default_text_channel[0]

    def __get_thread_history_with_default_name(self, text_channel: TextChannel | None) -> Thread | None:
        if text_channel is None:
            return None

        default_threads: typing.Tuple[Thread] = tuple(filter(
            lambda t: t.name == self._thread.config["history_thread_default_name"].lower(),
            text_channel.threads))

        if default_threads is None or len(default_threads) == 0:
            return None
        return default_threads[0]

    @staticmethod
    def __try_invoke(func: typing.Callable[[int], None] | None, value: int) -> None:
        if func is None:
            return
        func(value)
