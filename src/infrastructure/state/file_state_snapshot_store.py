from __future__ import annotations

"""Файловая реализация хранилища снапшотов state.

Снапшоты сохраняются в JSON‑файлы в директории ``local_run/state`` по
умолчанию. Имя файла формируется из ключа (``key``) путём простой
"очистки" символов, чтобы позже можно было заменить backend на Redis,
не меняя контракт :class:`IStateSnapshotStore`.
"""

import json
from pathlib import Path
from typing import Any, Dict

from src.domain.interfaces.state_snapshot_store import IStateSnapshotStore
from src.infrastructure.logging.logging_setup import log_stage


def _key_to_filename(key: str) -> str:
    """Преобразовать строковый ключ в безопасное имя файла.

    На данном этапе достаточно заменить ``/``, ``\\`` и ``:`` на
    безопасные символы и удалить пробелы. Формат имени стабилен и
    детерминирован.
    """

    cleaned = (
        key.replace("\\", "__")
        .replace("/", "__")
        .replace(":", "_")
        .replace(" ", "_")
    )
    return f"{cleaned}.json"


class FileStateSnapshotStore(IStateSnapshotStore):  # type: ignore[misc]
    """Файловое backend‑хранилище снапшотов state.

    Используется ранним прототипом; в будущем его можно заменить на
    Redis‑реализацию с тем же интерфейсом.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path("storage") / "state"
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        return self._base_dir / _key_to_filename(key)

    def save_snapshot(self, key: str, snapshot: Dict[str, Any]) -> None:  # type: ignore[override]
        path = self._path_for_key(key)
        try:
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(path)
            log_stage(
                "STATE",
                "Снапшот state сохранён в файл",
                key=key,
                path=str(path),
            )
        except OSError as exc:  # pragma: no cover - защитный путь
            log_stage(
                "ERROR",
                "Не удалось сохранить снапшот state",
                key=key,
                path=str(path),
                error=str(exc),
            )

    def load_snapshot(self, key: str) -> Dict[str, Any] | None:  # type: ignore[override]
        path = self._path_for_key(key)
        if not path.is_file():
            return None

        try:
            text = path.read_text(encoding="utf-8")
            snapshot = json.loads(text)
            if not isinstance(snapshot, dict):
                raise ValueError("Snapshot root must be a JSON object")
            log_stage(
                "LOAD",
                "Снапшот state загружен из файла",
                key=key,
                path=str(path),
            )
            return snapshot
        except (OSError, ValueError) as exc:  # pragma: no cover - защитный путь
            log_stage(
                "ERROR",
                "Не удалось загрузить снапшот state",
                key=key,
                path=str(path),
                error=str(exc),
            )
            return None


__all__ = ["FileStateSnapshotStore"]
