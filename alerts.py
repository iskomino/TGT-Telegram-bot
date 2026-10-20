"""Уведомления администраторам и пользователям (на языке получателя), общие тексты карточек."""
import asyncio
import html
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import content
import data
import db
from admin_texts import at
from config import ADMIN_IDS
from store import get_lang

logger = logging.getLogger(__name__)


def _kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows]
    )


def club_name(slug: str, lang: str) -> str:
    club = next((c for c in data.CLUBS if c["slug"] == slug), None)
    return club["name"][lang] if club else slug


def contact_html(item: dict) -> str:
    if item.get("username"):
        return f"@{html.escape(item['username'])}"
    return f'<a href="tg://user?id={int(item["user_id"])}">Telegram</a>'


# ---------- заявки в клубы ----------

def app_text(lang: str, app: dict) -> str:
    return at(
        lang,
        "app_view",
        id=app["id"],
        club=html.escape(club_name(app["club"], lang)),
        name=html.escape(app["name"]),
        faculty=html.escape(app["faculty"]),
        phone=html.escape(app["phone"]) if app["phone"] else "—",
        contact=contact_html(app),
        created=content.format_dt(app["created"]),
    )


def app_markup(lang: str, app_id: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            [(at(lang, "btn_accept"), f"adm:apo:{app_id}"), (at(lang, "btn_decline"), f"adm:apn:{app_id}")],
            [(at(lang, "btn_back"), "adm:ap")],
        ]
    )


# ---------- обращения ----------

def feedback_text(lang: str, fb: dict) -> str:
    if fb["anonymous"]:
        sender = at(lang, "fb_anon")
    else:
        sender = html.escape(fb["sender"] or "—") + (f" · @{html.escape(fb['username'])}" if fb["username"] else "")
    return at(
        lang,
        "fb_view",
        id=fb["id"],
        kind=at(lang, f"kind_{fb['kind']}"),
        sender=sender,
        created=content.format_dt(fb["created"]),
        text=html.escape(fb["text"]),
    )


def feedback_markup(lang: str, fb_id: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            [(at(lang, "btn_reply"), f"adm:fbr:{fb_id}"), (at(lang, "btn_close"), f"adm:fbc:{fb_id}")],
            [(at(lang, "btn_mute"), f"adm:fbm:{fb_id}")],
            [(at(lang, "btn_back"), "adm:fb")],
        ]
    )


# ---------- отправка ----------

async def notify_admins(bot: Bot, builder) -> int:
    """Отправляет всем администраторам сообщение на их языке. builder(lang) -> (текст, клавиатура)."""
    delivered = 0
    for admin_id in ADMIN_IDS:
        text, markup = builder(get_lang(admin_id))
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
            delivered += 1
        except Exception:  # noqa: BLE001 - один недоступный админ не должен мешать остальным
            logger.warning("Не удалось уведомить администратора %s", admin_id)
    return delivered


async def alert_new_application(bot: Bot, app_id: int) -> int:
    app = await db.get_application(app_id)
    if app is None:
        return 0
    return await notify_admins(bot, lambda lang: (at(lang, "app_alert_head") + app_text(lang, app), app_markup(lang, app_id)))


async def alert_new_feedback(bot: Bot, fb_id: int) -> int:
    fb = await db.get_feedback(fb_id)
    if fb is None:
        return 0
    return await notify_admins(bot, lambda lang: (at(lang, "fb_alert_head") + feedback_text(lang, fb), feedback_markup(lang, fb_id)))


async def send_localized(bot: Bot, user_ids: list[int], builder) -> dict[str, int]:
    """Отправляет каждому пользователю сообщение на его языке. builder(lang) -> (текст, клавиатура | None)."""
    stats = {"sent": 0, "blocked": 0, "failed": 0}
    for uid in user_ids:
        text, markup = builder(get_lang(uid))
        try:
            try:
                await bot.send_message(uid, text, reply_markup=markup)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                await bot.send_message(uid, text, reply_markup=markup)
            stats["sent"] += 1
        except TelegramForbiddenError:
            stats["blocked"] += 1
            await db.mark_blocked(uid)
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить сообщение пользователю %s", uid)
            stats["failed"] += 1
        await asyncio.sleep(0.05)  # ~20 сообщений/с, ниже лимита Telegram
    return stats
