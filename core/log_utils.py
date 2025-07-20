import logging
import logging.handlers


class CactusBotLogger(logging.Logger):
    pass


name_log = "cactus_discord_bot_logs.log"


def create_log_handler() -> logging.handlers.RotatingFileHandler:
    global name_log

    handler = logging.handlers.RotatingFileHandler(
        filename=name_log,
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,
        backupCount=5
    )
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', "%Y-%m-%d %H:%M:%S", style='{')
    handler.setFormatter(formatter)
    return handler


# Очистим данные прошлого запуска
with open(name_log, "w", encoding="utf-8") as f:
    f.truncate(0)

logging.setLoggerClass(CactusBotLogger)

log_level = logging.INFO
log_handler = create_log_handler()

# Добавляем логирование для discord.py
for discord_logger_name in ("discord", "discord.http", "discord.gateway", "discord.client", "discord.voice_client"):
    discord_logger = logging.getLogger(discord_logger_name)
    discord_logger.setLevel(logging.INFO)
    discord_logger.addHandler(log_handler)
    discord_logger.propagate = False


def get_logger(name: str | None = None) -> CactusBotLogger:
    global log_level, log_handler

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger.propagate = False

    return logger  # type: ignore
