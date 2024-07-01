import os
from pathlib import Path

from dotenv import load_dotenv

from core.log_utils import get_logger

logger = get_logger(__name__)


def get_project_root():
    return Path(__file__).parent.parent


def load_env() -> None:
    load_dotenv(get_env_path())


def get_env_path() -> str:
    return os.path.join(get_project_root(), ".env")


def get_path_to_music(name_track: str) -> str:
    path_to_folder = os.path.join(get_project_root(), "static\\music")
    if not os.path.isdir(path_to_folder):
        os.makedirs(path_to_folder)
    return os.path.join(path_to_folder, "{0}.mp3".format(name_track))


def get_path_to_messages_json() -> str:
    path = os.path.join(get_project_root(), "messages.json")
    return path


def check_existence_of_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    return os.path.exists(path)
