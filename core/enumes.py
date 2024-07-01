from enum import Enum


class MusicCommandType(str, Enum):
    FAVORITE = "fh"
    URL = "url"
    SEARCH = "sh"
    NOT_FOUND = "error"
    PLAY = "play"


class UrlType(Enum):
    IS_ALBUM = 0
    IS_PLAYLIST = 1
    IS_ARTIST = 2
    IS_ONE_TRACK = 3
