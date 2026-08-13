"""
Конфигурация проекта. Все секреты и параметры окружения читаются из .env
(или из переменных окружения, которые задаёт хостинг — например Railway).
Ничего из этого не хардкодится в коде.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_int_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
            result.append(int(part))
    return result


def _normalize_database_url(raw: str) -> str:
    """
    Railway/Render/Heroku и т.п. обычно выдают DATABASE_URL в виде
    postgres://... или postgresql://... — для async-драйвера asyncpg
    нужен диалект postgresql+asyncpg://. Приводим автоматически, чтобы
    ничего не нужно было руками менять в переменных окружения хостинга.
    """
    if raw.startswith("postgres://"):
        return "postgresql+asyncpg://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        return "postgresql+asyncpg://" + raw[len("postgresql://"):]
    return raw


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # Начальные супер-админы (Telegram ID через запятую).
    # После первого запуска управление админами полностью идёт через /admin.
    super_admin_ids: list[int] = field(default_factory=lambda: _get_int_list(os.getenv("SUPER_ADMIN_IDS")))

    database_url: str = field(
        default_factory=lambda: _normalize_database_url(
            os.getenv("DATABASE_URL", "postgresql+asyncpg://shop:shop@localhost:5432/shop")
        )
    )

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    uploads_dir: str = os.getenv("UPLOADS_DIR", "uploads")

    # Сколько сообщений рассылки отправлять в секунду (защита от лимитов Telegram)
    broadcast_rate_per_sec: float = float(os.getenv("BROADCAST_RATE_PER_SEC", "20"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()

if not config.bot_token:
    raise RuntimeError("BOT_TOKEN не задан. Укажите его в переменных окружения (.env локально, Variables на Railway).")

