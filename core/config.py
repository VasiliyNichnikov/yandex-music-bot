import json
import os
import typing
from copy import deepcopy

from core.errors import InvalidConfigError
from core.log_utils import get_logger
from core.path_utils import load_env, get_path_to_messages_json

logger = get_logger(__name__)

load_env()


class ConfigManager:
    """
        Конфигурация со всеми настройками
    """

    public_keys = {
        "prefix": "!",
        "message_content_name": "Музыка",
        "recent_auditions_title": "Вы недавно слушали:",
        "channel_with_music_default_name": "музыка",  # Название канала по умолчанию для прослушивания трека. (На случай если канал создан заранее)
        "history_thread_default_name": "история",  # Название ветки по умолчанию для истории треков. (На случай если ветка создана заранее)
        "default_icon_url_vk": "https://sun9-56.userapi.com/impg/p6aGXemp7cGozSNzNmTTHtsyTSuDkyo4GVLtnQ/tHFizKgaMDg.jpg?size=1024x1024&quality=95&sign=a063aaa51b89642075129f8fdbbbeef3&type=album",
        "messages": None,  # подгружается из json
        "message_lifetime": 30,  # Дефолтное время жизние сообщения, если не удалось посчитать кол-во слов в предложение
        "database_url": "mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4",
        "maximum_number_recent_requests_in_message":  5, # Не более 10. Так как дискорд за раз может отправить только 10 Embed
        "max_tracks_in_list": 3,  # Сколько максимально будем держать скаченных треков (Для одного канала)
        "commands_that_ignore_music_text_channel": ["help", "recreate"],  # Команды, которые можно вызывать из любого текстового канала
        "number_of_attempts_when_requesting_music_service": 10,   # Кол-во попыток при возникновение ошибке при запросе
        "delay_in_case_of_error_when_requesting_music_service": 30,  # Время ожидания прежде чем выполним следующий запрос к сервису
        "loading_tracks_into_ram": False,  # Куда загружаем треки, если RAM = false, то грузим на жесткий диск (пока поддерживается только жесткий диск). TODO: На текущие момент не поддерживается загрузка из ОЗУ
        "maximum_display_of_tracks_in_queue": 10,  # Максимальное кол-во треков, которое показываем в очереди. ВАЖНО: число должно быть меньше 25. Так как мы рисуем с помощью embed
    }

    # Доступные команды и команды на отключение
    # Важно: ключ - равен названию команды
    # Значение говорит о том доступна команда или нет,
    # True - доступна, False - не доступна
    available_commands = {
        "play": True,
        "fh": False,
        "url": False,
        "sh": False,
        "prev": True,
        "next": True,
        "loop": True,
        "pause": True,
        "stop": True,
        "queue": True
    }

    protected_keys = {
        "discord_token": None,
        "yandex_token": None,
        "is_production": False,

        "database_user": None,
        "database_password": None,
        "database_name": None,
        "database_host": None,
        "database_port": None,
        "owner_bot_id": None
    }

    dev_keys = {
        "ignore_number_members_in_voice_chat": True,
        "waiting_time_before_disconnection": 10,
        "ignore_user_in_voice_channel": True,
        "slash_supported": False
    }

    production_keys = {
        "ignore_number_members_in_voice_chat": False,
        "waiting_time_before_disconnection": 360,
        "ignore_user_in_voice_channel": False,
        "slash_supported": True  # Включает команды через "/"
    }

    __defaults = {**public_keys, **protected_keys, **production_keys, **available_commands}
    __all_keys = set(__defaults.keys())

    def __init__(self) -> None:
        self._cache = {}

    def init_cache(self) -> typing.Dict:
        """
            Инициализация конфига
        """
        data = deepcopy(self.__defaults)

        # Достаем из .env
        data.update({key.lower(): value for key, value in os.environ.items() if key.lower() in self.__all_keys})

        # Добавляем данные в зависимости от прода/разработки
        if data["is_production"].lower() == "True".lower():
            logger.info("Loading production keys.")
            data.update(**self.production_keys)
        else:
            logger.info("Loading dev keys.")
            data.update(**self.dev_keys)
        # Далее можем брать из json, но нам это пока не нужно

        with open(get_path_to_messages_json(), "r", encoding="utf-8") as file_read:
            loaded_messages = json.load(file_read)
            data["messages"] = loaded_messages

        self._cache = data

        return self._cache

    def __getitem__(self, key: str) -> typing.Any:
        return self.get(key)

    def get(self, key: str) -> typing.Any:
        key = key.lower()

        if key not in self.__all_keys:
            raise InvalidConfigError(f"Configuration {key} is invalid")

        if key not in self._cache:
            self._cache[key] = deepcopy(self.__defaults[key])

        value = self._cache[key]
        return value

    def get_unsafe(self, key: str) -> typing.Any | None:
        if not isinstance(key, str):
            return None

        key = key.lower()

        if key not in self.__defaults:
            return None

        if key not in self._cache:
            self._cache[key] = deepcopy(self.__defaults[key])

        value = self._cache[key]
        return value
