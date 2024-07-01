import re


# Средняя скорость чтения слов в минуту
WORDS_PER_MINUTE = 120


def get_reading_time(text: str) -> float:
    global WORDS_PER_MINUTE

    word_count = __get_word_count(text)
    seconds = word_count % WORDS_PER_MINUTE / (WORDS_PER_MINUTE / 60)
    return seconds


def __get_word_count(text: str) -> int:
    words = re.split(r"\s+", text)
    return len(words)
