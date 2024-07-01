"""
    Все команды, которые поддерживает бот
    Вынес отдельно, чтобы они не зависели от точки входа
"""
from bot import CactusDiscordBot
from core.interaction import SenderMessagesWithGuild
from core.log_utils import get_logger
from core.playerfacade import PlayerFacade
from core.string_utils import check_yandex_url

logger = get_logger(__name__)


async def play_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, request: str) -> None:
    """
        Совмещает в себя все команды
    """
    api = bot.yandex_music_api
    yandex_music_api = api.get_automatic_request(request=request, max_tracks=1)

    thread = bot.thread_manager.get_thread_by_guild_id(interaction.guild_id)
    content = bot.config["messages"]["command_play_running"]

    await bot.message_manager.send_message(interaction, content=content)
    await thread.player.add_track_request_and_play(yandex_music_api)


async def favorite_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot) -> None:
    api = bot.yandex_music_api
    yandex_music_api = api.get_request_from_favorite(index=0)
    thread = bot.thread_manager.get_thread_by_guild_id(interaction.guild_id)

    content = bot.config["messages"]["command_favorite_running"]

    await bot.message_manager.send_message(interaction, content=content)
    await thread.player.add_track_request_and_play(yandex_music_api)


async def url_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, url: str) -> None:
    api = bot.yandex_music_api
    yandex_music_request = api.get_request_by_url(url=url)
    thread = bot.thread_manager.get_thread_by_guild_id(interaction.guild_id)

    content = bot.config["messages"]["command_url_running"]

    await bot.message_manager.send_message(interaction, content=content)
    await thread.player.add_track_request_and_play(yandex_music_request)


async def search_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, search: str) -> None:
    api = bot.yandex_music_api
    # Значит данные пришли от поиска (через слэш)
    if check_yandex_url(url=search):
        logger.debug(f"Run search command. Url: {search}")
        yandex_music_request = api.get_request_by_url(url=search)
    else:
        if len(search) > 100:
            search = search[:100]
        logger.debug(f"Run search command. Search: {search}")
        yandex_music_request = api.get_request_by_search(search=search, max_tracks=1)

    thread = bot.thread_manager.get_thread_by_guild_id(interaction.guild_id)
    content = bot.config["messages"]["command_search_running"]

    await bot.message_manager.send_message(interaction, content=content)
    await thread.player.add_track_request_and_play(yandex_music_request)


async def recreate_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot) -> None:
    thread = bot.thread_manager.get_thread_by_guild_id(guild_id=interaction.guild_id)

    if thread is None:
        return

    await thread.update()
    content = bot.config["messages"]["recreate_command_completed"]
    await bot.message_manager.send_message(interaction, content=content)


async def previous_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, player: PlayerFacade) -> None:
    await player.preview_track()
    message = bot.config["messages"]["previous_command_completed"]
    await bot.message_manager.send_message(interaction, content=message)


async def next_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, player: PlayerFacade) -> None:
    await player.next_track()
    message = bot.config["messages"]["next_command_completed"]
    await bot.message_manager.send_message(interaction, content=message)


async def loop_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, player: PlayerFacade) -> None:
    await player.change_loop(show_message=False)
    if player.is_loop():
        message = bot.config["messages"]["loop_command_completed_on"]
    else:
        message = bot.config["messages"]["loop_command_completed_off"]
    await bot.message_manager.send_message(interaction, content=message)


async def pause_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, player: PlayerFacade) -> None:
    await player.pause_track()
    if player.is_paused():
        message = bot.config["messages"]["pause_command_completed_on"]
    else:
        message = bot.config["messages"]["pause_command_completed_off"]
    await bot.message_manager.send_message(interaction, content=message)


async def stop_command(interaction: SenderMessagesWithGuild, bot: CactusDiscordBot, player: PlayerFacade) -> None:
    await player.stop_track(disconnect=False)
    message = bot.config["messages"]["stop_command_completed"]
    await bot.message_manager.send_message(interaction, content=message)
