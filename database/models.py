from sqlalchemy import BigInteger, Integer, ForeignKey
from sqlalchemy import String, Column, DateTime, Boolean
from sqlalchemy.orm import relationship

from database.basemodel import BaseModel


class RequestToMusicModel(BaseModel):
    """
        Содержит запрос который был отправлен для проигрывания
    """
    __tablename__ = "requests_to_music"

    name_command = Column(String(50), nullable=False)
    title = Column(String(500), nullable=True)
    request = Column(String(300), nullable=False)
    date_time = Column(DateTime, nullable=False)
    is_playlist = Column(Boolean, default=False)
    is_album = Column(Boolean, default=False)
    is_artist = Column(Boolean, default=False)
    is_one_track = Column(Boolean, default=False)
    user_name_playlist = Column(String, nullable=True)
    album_name_track = Column(String, nullable=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"))


class GuildModel(BaseModel):
    __tablename__ = "guilds"

    guild_id = Column(BigInteger, nullable=False)
    text_channel_id = Column(BigInteger, nullable=False)
    thread_id = Column(BigInteger, nullable=False)
    requests_to_music = relationship("RequestToMusicModel", backref="guild")
