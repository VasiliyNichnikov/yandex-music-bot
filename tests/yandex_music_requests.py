import pytest
import pytest_asyncio

from core.config import ConfigManager
from requests_to_music_service.executing_requests import ExecutingRequests
from storage.storage import Storage
from yandex.client import YandexMusicAccount


@pytest_asyncio.fixture
async def client() -> YandexMusicAccount:
    config = ConfigManager()
    config.init_cache()
    account = YandexMusicAccount(config)
    await account.init()

    return account


@pytest.mark.asyncio
async def test_get_one_track_request(client: YandexMusicAccount) -> None:
    """
        Тестируем запрос к треку "Цветы"
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_url("https://music.yandex.ru/album/30847724/track/125145915")
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]
    assert playlist.title.lower() == "цветы"
    assert len(playlist.tracks) == 1


@pytest.mark.asyncio
async def test_get_album_request(client: YandexMusicAccount) -> None:
    """
        Тестируем запрос к альбому "Сердце не бьется"
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_url("https://music.yandex.ru/album/29719904")
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]

    assert len(playlist.tracks) == 9


@pytest.mark.asyncio
async def test_get_playlist_on_repeat_request(client: YandexMusicAccount) -> None:
    """
        Тестируем запрос к плейлисту "На повторе"
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_url("https://music.yandex.ru/users/nichnikov.vasily/playlists/1015")
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]

    assert len(playlist.tracks) == 3


@pytest.mark.asyncio
async def test_get_book_request(client: YandexMusicAccount) -> None:
    """
        Тестирование запроса для получения аудиокниги "Мо Янь. «Смерть пахнет сандалом»"
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_url("https://music.yandex.ru/album/30059493?activeTab=about")
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]

    assert len(playlist.tracks) == 21


@pytest.mark.asyncio
async def test_get_podcast_request(client: YandexMusicAccount) -> None:
    """
            Тестирование запроса для получения подкаста "Голоса московских домов"
        """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_url("https://music.yandex.ru/album/31122855/track/125745689?activeTab=track-list&dir=desc")
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]

    assert len(playlist.tracks) == 1


@pytest.mark.asyncio
async def test_get_track_by_search(client: YandexMusicAccount) -> None:
    """
        Возвращаем трек используя поиск, название трека "дора дура"
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_search("дора дура", 1)
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)
    # В конце получим треки и проверим их кол-во
    playlist = storage.get_loaded_playlists()[0]

    assert len(playlist.tracks) == 1
    assert playlist.title.lower() == "дора дура"
    assert playlist.tracks[0].title.lower() == "дора дура"


@pytest.mark.asyncio
async def test_get_non_existent_track(client: YandexMusicAccount) -> None:
    """
            Возвращаем трек используя поиск, трека с введеным значением не существует
    """

    # Создаем обработчик запросов
    executing_request = ExecutingRequests(5, 5)
    # Создаем запрос
    request = client.get_request_by_search("ajdjkdfdjskhfkjdsfgsdgfhsgdt6234278adjfdshjgjhdsfgdj", 1)
    # Далее нужно хранилище для работы с запросом
    storage = Storage(executing_request)
    await storage.add(request)

    assert len(storage.get_loaded_playlists()) == 0
