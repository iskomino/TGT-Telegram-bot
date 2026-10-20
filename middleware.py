import logging
import time
from collections import deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

import db
from store import get_lang
from texts import BUTTON_TO_SECTION, t

logger = logging.getLogger(__name__)


class StatsMiddleware(BaseMiddleware):
    """Записывает активность пользователя (ID и раздел меню) для статистики. Тексты сообщений не сохраняются."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        try:
            if event.from_user and event.chat.type == "private":
                await db.touch_user(event.from_user.id, BUTTON_TO_SECTION.get(event.text or ""))
        except Exception:  # noqa: BLE001 - статистика не должна ломать бота
            logger.exception("Не удалось записать статистику")
        return await handler(event, data)


class ThrottlingMiddleware(BaseMiddleware):
    """Защита от спама: не больше `limit` действий (сообщений и нажатий кнопок) за `window` секунд от одного пользователя.

    Лишние действия отбрасываются, пользователь один раз за окно получает предупреждение.
    Администраторы из `exempt` не ограничиваются.
    """

    def __init__(self, limit: int = 10, window: float = 10.0, exempt=()):
        self.limit = limit
        self.window = window
        self.exempt = set(exempt)
        self._hits: dict[int, deque] = {}
        self._warned: dict[int, float] = {}
        self._now = time.monotonic  # подменяется в тестах

    def _cleanup(self, now: float) -> None:
        for uid in [u for u, hits in self._hits.items() if not hits or now - hits[-1] > self.window]:
            self._hits.pop(uid, None)
            self._warned.pop(uid, None)

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None or user.id in self.exempt:
            return await handler(event, data)

        now = self._now()
        hits = self._hits.setdefault(user.id, deque())
        while hits and now - hits[0] > self.window:
            hits.popleft()

        if len(hits) >= self.limit:
            await self._warn(event, user.id, now)
            return None

        hits.append(now)
        if len(self._hits) > 5000:
            self._cleanup(now)
        return await handler(event, data)

    async def _warn(self, event: Message | CallbackQuery, uid: int, now: float) -> None:
        first_warning = now - self._warned.get(uid, float("-inf")) >= self.window
        if first_warning:
            self._warned[uid] = now
        text = t(get_lang(uid), "throttled")
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(text if first_warning else None)  # всегда отвечаем, чтобы кнопка не «крутилась»
            elif first_warning:
                await event.answer(text)
        except Exception:  # noqa: BLE001
            logger.debug("Не удалось отправить предупреждение о частоте запросов", exc_info=True)
