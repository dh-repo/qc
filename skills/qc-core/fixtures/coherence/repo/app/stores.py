"""Planted P1: two implementations of delete() are not observably equivalent."""


class MemoryStore:
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def delete(self, item_id: str) -> None:
        self._rows.pop(item_id, None)


class FileStore:
    def delete(self, item_id: str) -> None:
        raise FileNotFoundError(item_id)
