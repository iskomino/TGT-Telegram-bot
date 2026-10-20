"""Мероприятия для студентов: список, карточка, запись и отмена записи."""
import html
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import content
import db
from flows import is_btn
from store import get_lang
from texts import t

events_router = Router(name="events")
events_router.message.filter(F.chat.type == "private")

SHOW_STARTED_FOR = 3600  # мероприятие остаётся в списке ещё час после начала


def render_event(lang: str, event: dict, *, with_count: bool = True) -> str:
    lines = [f"📅 <b>{html.escape(event['title'])}</b>", "", f"🗓 {content.format_dt(event['starts_at'])}"]
    if event.get("place"):
        lines.append(f"📍 {html.escape(event['place'])}")
    if event.get("description"):
        lines += ["", html.escape(event["description"])]
    if with_count:
        if event.get("capacity"):
            counter = t(lang, "ev_registered_cap", count=event["registered"], capacity=event["capacity"])
        else:
            counter = t(lang, "ev_registered", count=event["registered"])
        lines += ["", counter]
    return "\n".join(lines)


def events_list_inline(lang: str, events: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📅 {content.short_dt(e['starts_at'])} · {e['title']}"[:60], callback_data=f"ev:{e['id']}")]
            for e in events
        ]
    )


def event_inline(lang: str, event_id: int, registered: bool, can_register: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_register:
        if registered:
            rows.append([InlineKeyboardButton(text=t(lang, "btn_unregister"), callback_data=f"evu:{event_id}")])
        else:
            rows.append([InlineKeyboardButton(text=t(lang, "btn_register"), callback_data=f"evr:{event_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back_inline"), callback_data="ev:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_inline(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"⭐{n}", callback_data=f"rate:{event_id}:{n}") for n in range(1, 6)]]
    )


def open_event_inline(lang: str, event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_open_event"), callback_data=f"ev:{event_id}")]]
    )


async def _upcoming() -> list[dict]:
    return await db.list_events(int(time.time()) - SHOW_STARTED_FOR, limit=10)


async def _edit(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


async def _show_list(lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    events = await _upcoming()
    if not events:
        return t(lang, "events_empty"), None
    return t(lang, "events_title"), events_list_inline(lang, events)


async def _show_card(call: CallbackQuery, lang: str, event_id: int) -> None:
    event = await db.get_event(event_id)
    if event is None:
        await _edit(call, t(lang, "ev_missing"), None)
        return
    registered = await db.is_registered(event_id, call.from_user.id)
    can_register = event["starts_at"] > time.time()
    await _edit(call, render_event(lang, event), event_inline(lang, event_id, registered, can_register))


@events_router.message(is_btn("btn_events"))
async def events_menu(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    text, markup = await _show_list(lang)
    await message.answer(text, reply_markup=markup)


@events_router.callback_query(F.data.startswith("ev:"))
async def cb_event(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    raw = (call.data or "").split(":", 1)[-1]
    if raw == "list":
        await call.answer()
        text, markup = await _show_list(lang)
        await _edit(call, text, markup)
        return
    if not raw.isdigit():
        await call.answer()
        return
    event = await db.get_event(int(raw))
    if event is None:
        await call.answer(t(lang, "ev_missing"), show_alert=True)
        return
    await call.answer()
    await _show_card(call, lang, int(raw))


def _display_name(call: CallbackQuery) -> str:
    return (call.from_user.full_name or "")[:60]


@events_router.callback_query(F.data.startswith("evr:"))
async def cb_register(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    raw = (call.data or "").split(":", 1)[-1]
    if not raw.isdigit():
        await call.answer()
        return
    status = await db.register(int(raw), call.from_user.id, _display_name(call), call.from_user.username or "")
    key = {"ok": "reg_ok", "already": "reg_already", "full": "reg_full", "closed": "reg_closed", "missing": "ev_missing"}[status]
    await call.answer(t(lang, key), show_alert=True)
    if status != "missing":
        await _show_card(call, lang, int(raw))


@events_router.callback_query(F.data.startswith("evu:"))
async def cb_unregister(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    raw = (call.data or "").split(":", 1)[-1]
    if not raw.isdigit():
        await call.answer()
        return
    event = await db.get_event(int(raw))
    if event is not None and event["starts_at"] <= time.time():  # после начала запись не отменяется (идёт учёт посещаемости)
        await call.answer(t(lang, "reg_closed"), show_alert=True)
        await _show_card(call, lang, int(raw))
        return
    await db.unregister(int(raw), call.from_user.id)
    await call.answer(t(lang, "unreg_ok"), show_alert=True)
    await _show_card(call, lang, int(raw))


@events_router.callback_query(F.data.regexp(r"^rate:\d+:[1-5]$"))
async def cb_rate(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    _, raw_id, raw_rating = (call.data or "").split(":")
    status = await db.set_rating(int(raw_id), call.from_user.id, int(raw_rating))
    if status == "ok":
        await call.answer()
        await _edit(call, t(lang, "rate_thanks", stars="⭐" * int(raw_rating)), None)
    elif status == "already":
        await call.answer(t(lang, "rate_already"), show_alert=True)
    else:
        await call.answer(t(lang, "rate_invalid"), show_alert=True)
