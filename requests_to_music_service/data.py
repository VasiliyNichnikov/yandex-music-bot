import dataclasses


@dataclasses.dataclass
class InfoAboutRequest:
    title: str
    is_album: bool
    is_playlist: bool
    is_artist: bool
    is_track: bool
    url: str
    user_name_playlist: str | None  # Какой пользователь содержит этот плейлист
    album_name_track: str | None  # Какай альбом содержит трек


def create_for_album(title: str, url: str) -> InfoAboutRequest:
    return InfoAboutRequest(title=title,
                            is_album=True,
                            is_playlist=False,
                            is_artist=False,
                            is_track=False,
                            url=url,
                            user_name_playlist=None,
                            album_name_track=None)


def create_for_one_track(title: str, url: str, album_name_track: str) -> InfoAboutRequest:
    return InfoAboutRequest(title=title,
                            is_album=False,
                            is_playlist=False,
                            is_artist=False,
                            is_track=True,
                            url=url,
                            user_name_playlist=None,
                            album_name_track=album_name_track)


def create_for_playlist(title: str, url: str, user_name_playlist: str) -> InfoAboutRequest:
    return InfoAboutRequest(title=title,
                            is_album=False,
                            is_playlist=True,
                            is_artist=False,
                            is_track=False,
                            url=url,
                            user_name_playlist=user_name_playlist,
                            album_name_track=None)


def create_for_artist(title: str, url: str) -> InfoAboutRequest:
    return InfoAboutRequest(title=title,
                            is_album=False,
                            is_playlist=False,
                            is_artist=True,
                            is_track=False,
                            url=url,
                            user_name_playlist=None,
                            album_name_track=None)


def create_empty() -> InfoAboutRequest:
    return InfoAboutRequest(title="",
                            is_album=False,
                            is_playlist=False,
                            is_artist=False,
                            is_track=False,
                            url="",
                            user_name_playlist=None,
                            album_name_track=None)
