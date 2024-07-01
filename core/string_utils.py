import re


def check_yandex_url(url: str) -> bool:
    pattern = re.compile("^https://music.yandex.ru/album/[1-9][0-9]*/track/[1-9][0-9]*")
    match = pattern.match(url)
    if match is None:
        return False
    return match.string == url
