import os.path
import subprocess
from core.log_utils import get_logger


logger = get_logger(__name__)


def get_duration_track(track_path: str) -> float:
    if not os.path.exists(track_path):
        logger.error("Path to the file was not found")
        return 0

    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", track_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)
