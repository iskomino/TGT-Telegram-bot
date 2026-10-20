"""Фоновая задача: напоминания о мероприятиях за сутки и ежедневная очистка устаревших данных."""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

import db
from events import open_event_inline, render_event
from store import get_lang
from texts import t

logger = logging.getLogger(__name__)


async def send_due(bot: Bot) -> int:
    """Отправляет все напоминания, срок которых наступил. Возвращает число отправленных."""
    sent = 0
    events: dict[int, dict | None] = {}
    for item in await db.due_reminders():
        event_id, uid = item["event_id"], item["user_id"]
        if event_id not in events:
            events[event_id] = await db.get_event(event_id)
        event = events[event_id]
        if event is None:
            continue
        lang = get_lang(uid)
        text = t(lang, "event_reminder", card=render_event(lang, event, with_count=False))
        markup = open_event_inline(lang, event_id)
        try:
            try:
                await bot.send_message(uid, text, reply_markup=markup)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                await bot.send_message(uid, text, reply_markup=markup)
            sent += 1
        except TelegramForbiddenError:
            await db.mark_blocked(uid)
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить напоминание (событие %s, пользователь %s)", event_id, uid)
        await db.mark_reminded(event_id, uid)  # в любом случае: повторять бесконечно нет смысла
        await asyncio.sleep(0.05)
    return sent


async def reminders_loop(bot: Bot, interval: float = 60.0) -> None:
    ticks = 0
    while True:
        try:
            await send_due(bot)
            ticks += 1
            if ticks % 1440 == 0:  # раз в сутки при интервале в минуту
                await db.purge_old()
        except Exception:  # noqa: BLE001 - цикл не должен останавливаться
            logger.exception("Сбой цикла напоминаний")
        await asyncio.sleep(interval)
