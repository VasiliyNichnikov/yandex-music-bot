import typing
from datetime import datetime

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session

from core.config import ConfigManager
from core.enumes import MusicCommandType, UrlType
from core.log_utils import get_logger
from core.recentrequest import OldRecentRequest, RecentRequestProtocol, PlayRecentRequest, RecentRequestAdditionalData
from database.models import GuildModel, RequestToMusicModel
from database.data import GuildData, RequestsToMusicData
from requests_to_music_service.data import InfoAboutRequest

logger = get_logger(__name__)


class ClientDataBaseAPI:
    def __init__(self, config: ConfigManager) -> None:
        self._config: ConfigManager = config
        self._session: None | Session = None

    def get_guild_data(self, guild_id: int) -> GuildData | None:
        with self.__Session() as session:
            model = self.__get_guild_without_create_session(guild_id, session)
            if model is None:
                return None
            data = self.__convert_guild_model_to_data(model)
        return data

    def create_guild_data(self, guild_id: int) -> GuildData:
        with self.__Session() as session:
            model = GuildModel(guild_id=guild_id, text_channel_id=0, thread_id=0)
            session.add(model)
            session.commit()
            data = self.__convert_guild_model_to_data(model)

        return data

    def update_guild_data(self, guild_id: int, text_channel_id: int | None, thread_id: int | None) -> None:
        with self.__Session() as session:
            guild = self.__get_guild_without_create_session(guild_id, session)
            if guild is None:
                logger.error(f"Guild with id {guild_id} does not.")
                return

            changed = False
            if text_channel_id is not None and guild.text_channel_id != text_channel_id:
                guild.text_channel_id = text_channel_id
                changed = True
            if thread_id is not None and guild.thread_id != thread_id:
                guild.thread_id = thread_id
                changed = True

            if changed:
                session.add(guild)
                session.commit()

    def delete_guild_data(self, guild_id: int) -> None:
        with self.__Session() as session:
            guild = self.__get_guild_without_create_session(guild_id, session)
            if guild is None:
                logger.error(f"Guild with id {guild_id} does not.")
                return

            session.delete(guild)
            session.commit()

    def add_or_update_music_request(self, guild_id: int, info: InfoAboutRequest, date_time: datetime) -> None:
        """
            Добавляет запрос в список и время запроса
            Если такой запрос уже есть, обновляем время
        """
        with self.__Session() as session:
            guild: GuildModel = self.__get_guild_without_create_session(guild_id, session)
            if guild is None:
                return

            request_to_music_model: RequestToMusicModel | None = None
            requests: typing.List[RequestToMusicModel] = guild.requests_to_music
            for item in requests:
                if item.guild.guild_id == guild_id and item.request == info.url:
                    request_to_music_model = item
                    break

            # Обновляем время если запрос не отличается от старого
            if request_to_music_model is not None and request_to_music_model.request == info.url:
                request_to_music_model.date_time = date_time
                session.add(request_to_music_model)
                session.commit()
                return

            created_request_to_music_model = RequestToMusicModel(guild_id=guild_id,
                                                                 title=info.title,
                                                                 request=info.url,
                                                                 date_time=date_time,
                                                                 is_album=info.is_album,
                                                                 is_playlist=info.is_playlist,
                                                                 is_artist=info.is_artist,
                                                                 is_one_track=info.is_track,
                                                                 user_name_playlist=info.user_name_playlist,
                                                                 album_name_track=info.album_name_track,
                                                                 name_command=MusicCommandType.PLAY.value)
            guild.requests_to_music.append(created_request_to_music_model)
            session.add(guild)
            session.commit()

    def get_all_requests_to_music(self, guild_id: int) -> typing.List[RequestsToMusicData]:
        with self.__Session() as session:
            model = self.__get_guild_without_create_session(guild_id, session)
            if model is None:
                return []
            data = self.__convert_guild_model_to_data(model)
        return data.requests_to_music

    @staticmethod
    def __get_guild_without_create_session(guild_id: int, session: Session,
                                           error_if_none: bool = False) -> GuildModel | None:
        model = session.query(GuildModel).filter(GuildModel.guild_id == guild_id).first()
        if error_if_none and model is None:
            logger.error(f"Guild with id {guild_id} does not.")
        return model

    @property
    def __Session(self) -> sessionmaker:
        if self._session is None:
            self._session = sessionmaker(bind=self.__create_engine())
        return self._session

    def __create_engine(self) -> Engine:
        user = self._config.get("database_user")
        password = self._config.get("database_password")
        database = self._config.get("database_name")
        host = self._config.get("database_host")
        port = self._config.get("database_port")

        url = self._config["database_url"].format(user=user, password=password, host=host, port=port, database=database)
        return create_engine(url)

    @staticmethod
    def __convert_guild_model_to_data(model: GuildModel | None) -> GuildData | None:
        if model is None:
            logger.error("Guild model is none.")
            return None

        requests: typing.List[RequestToMusicModel] = list(model.requests_to_music) if model.requests_to_music is not None else []
        converted_requests: typing.List[RequestsToMusicData] = []
        for request in requests:
            converted_request = RequestsToMusicData(
                name_command=request.name_command,
                url=request.request,
                date_time=request.date_time,
                guild_id=request.guild_id,
                title=request.title,
                is_album=request.is_album,
                is_playlist=request.is_playlist,
                is_artist=request.is_artist,
                is_track=request.is_one_track,
                user_name_playlist=request.user_name_playlist,
                album_name_track=request.album_name_track
            )
            converted_requests.append(converted_request)

        data = GuildData(guild_id=model.guild_id,
                         text_channel_id=model.text_channel_id,
                         thread_id=model.thread_id,
                         requests_to_music=converted_requests)
        return data


class ThreadDataBase:
    def __init__(self, config: ConfigManager, db_api: ClientDataBaseAPI, guild_id: int) -> None:
        self._db_api: ClientDataBaseAPI = db_api
        self._guild_id: int = guild_id
        self._config = config

    @property
    def guild_data(self) -> GuildData:
        guild_model = self._db_api.get_guild_data(self._guild_id)

        if guild_model is None:
            return self._db_api.create_guild_data(self._guild_id)
        return guild_model

    def update_channel_with_music(self, text_channel_id: int) -> None:
        self._db_api.update_guild_data(self._guild_id, text_channel_id, None)

    def update_history_thread(self, thread_id: int) -> None:
        self._db_api.update_guild_data(self._guild_id, None, thread_id)

    def add_music_request(self, info: InfoAboutRequest, date_time: datetime) -> None:
        self._db_api.add_or_update_music_request(self._guild_id, info, date_time)

    def delete(self) -> None:
        self._db_api.delete_guild_data(self._guild_id)

    def get_all_recent_requests(self) -> typing.Tuple[RecentRequestProtocol, ...]:
        recommendations: typing.List[RecentRequestProtocol] = []
        requests: typing.List[RequestsToMusicData] = self._db_api.get_all_requests_to_music(self._guild_id)

        for request in requests:
            if request.name_command == MusicCommandType.PLAY.value:
                url_type: UrlType = UrlType.IS_PLAYLIST
                if request.is_album:
                    url_type = UrlType.IS_ALBUM
                elif request.is_playlist:
                    url_type = UrlType.IS_PLAYLIST
                elif request.is_artist:
                    url_type = UrlType.IS_ARTIST
                elif request.is_track:
                    url_type = UrlType.IS_ONE_TRACK
                else:
                    logger.error(f"url type for request not found: {request}")

                additional_data = RecentRequestAdditionalData(user_name_playlist=request.user_name_playlist,
                                                              album_name_track=request.album_name_track)
                recommendation = PlayRecentRequest(self._config,
                                                   request.url,
                                                   request.title,
                                                   url_type,
                                                   additional_data,
                                                   request.date_time)
                recommendations.append(recommendation)
            else:
                match request.name_command:
                    case MusicCommandType.FAVORITE.value:
                        command_type = MusicCommandType.FAVORITE
                    case MusicCommandType.URL.value:
                        command_type = MusicCommandType.URL
                    case MusicCommandType.SEARCH.value:
                        command_type = MusicCommandType.SEARCH
                    case _:
                        logger.error(f"Unknown command type: {request.name_command}")
                        command_type = MusicCommandType.NOT_FOUND

                request_text = None if request.url == "" else request.url
                recommendation = OldRecentRequest(self._config, command_type, request_text, request.date_time)
                recommendations.append(recommendation)
        return tuple(recommendations)
