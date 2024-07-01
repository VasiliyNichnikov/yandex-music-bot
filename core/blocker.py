class Blocker:
    def __init__(self) -> None:
        self._is_blocked: bool = False

    def is_blocked(self) -> bool:
        return self._is_blocked

    def block(self) -> None:
        self._is_blocked = True

    def unlock(self) -> None:
        self._is_blocked = False