import logging
import logging.handlers


class CactusBotLogger(logging.Logger):
    pass


def create_log_handler() -> logging.handlers.RotatingFileHandler:
    handler = logging.handlers.RotatingFileHandler(
        filename="cactus_discord_bot_logs.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,
        backupCount=5
    )
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', "%Y-%m-%d %H:%M:%S", style='{')
    handler.setFormatter(formatter)
    return handler


logging.setLoggerClass(CactusBotLogger)
logging.getLogger("discord.http").setLevel(logging.INFO)

log_level = logging.INFO
log_handler = create_log_handler()


def get_logger(name: str | None = None) -> CactusBotLogger:
    global log_level, log_handler

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(log_handler)

    return logger  # type: ignore
