"""Админ-панель, часть 2: заявки в клубы, мероприятия, обращения (предложения и жалобы).

Роутер подключается ДО основного админ-роутера (см. main.py), чтобы его кнопки не перехватывал «устаревший» обработчик.
"""
import asyncio
import html
import logging
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import alerts
import content
import data
import db
from admin import _dash, _edit, _kb
from admin_texts import at
from config import ADMIN_IDS
from events import render_event
from flows import PLAIN_TEXT
from store import get_lang
from texts import t

logger = logging.getLogger(__name__)

admin_extra_router = Router(name="admin_extra")
admin_extra_router.message.filter(F.chat.type == "private", F.from_user.id.in_(ADMIN_IDS))
admin_extra_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

MUTE_DAYS = 7
MAX_FUTURE_DAYS = 2 * 365
_tasks: set[asyncio.Task] = set()


class EventCreate(StatesGroup):
    title = State()
    when = State()
    place = State()
    desc = State()
    cap = State()


class EventEdit(StatesGroup):
    value = State()


class FbReply(StatesGroup):
    text = State()


def _int(raw: str) -> int | None:
    return int(raw) if raw.isdigit() and len(raw) <= 12 else None


def _example_dt() -> str:
    return content.format_dt(int(time.time()) + 3 * 86400)


# ======================================================================
# Заявки в клубы
# ======================================================================

async def _apps_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    apps = await db.list_applications()
    total = await db.count_applications()
    rows = [
        [(f"№{a['id']} · {alerts.club_name(a['club'], lang)} · {a['name']}"[:60], f"adm:apv:{a['id']}")] for a in apps
    ]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    text = at(lang, "apps_title", count=total) if apps else at(lang, "apps_empty")
    return text, _kb(rows)


@admin_extra_router.callback_query(F.data == "adm:ap")
async def cb_apps(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = await _apps_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_extra_router.callback_query(F.data.startswith("adm:apv:"))
async def cb_app_view(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    app_id = _int((call.data or "").split(":")[-1])
    app = await db.get_application(app_id) if app_id is not None else None
    if app is None or app["status"] != "new":
        await call.answer(at(lang, "app_gone"), show_alert=True)
        text, markup = await _apps_view(lang)
        await _edit(call, text, markup)
        return
    await call.answer()
    await _edit(call, alerts.app_text(lang, app), alerts.app_markup(lang, app["id"]))


@admin_extra_router.callback_query(F.data.regexp(r"^adm:ap[on]:\d+$"))
async def cb_app_decide(call: CallbackQuery, bot: Bot):
    lang = get_lang(call.from_user.id)
    _, action, raw = (call.data or "").split(":")
    accept = action == "apo"
    app = await db.get_application(int(raw))
    if app is None or not await db.set_application_status(app["id"], "accepted" if accept else "declined"):
        await call.answer(at(lang, "app_gone"), show_alert=True)
    else:
        student_lang = get_lang(app["user_id"])
        delivered = True
        try:
            await bot.send_message(
                app["user_id"],
                t(student_lang, "app_accepted" if accept else "app_declined", club=html.escape(alerts.club_name(app["club"], student_lang))),
            )
        except TelegramForbiddenError:
            delivered = False
            await db.mark_blocked(app["user_id"])
        except Exception:  # noqa: BLE001
            delivered = False
            logger.exception("Не удалось уведомить студента о решении по заявке %s", app["id"])
        toast = at(lang, "app_accepted_admin" if accept else "app_declined_admin")
        if not delivered:
            toast += f" ({at(lang, 'notify_failed')})"
        await call.answer(toast[:200], show_alert=not delivered)
    text, markup = await _apps_view(lang)
    await _edit(call, text, markup)


# ======================================================================
# Мероприятия
# ======================================================================

async def _events_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    events = await db.list_events(int(time.time()) - 7 * 86400, limit=40)
    rows = [[(at(lang, "btn_new_event"), "adm:evnew")]]
    rows += [[(f"📅 {content.short_dt(e['starts_at'])} · {e['title']}"[:60], f"adm:evv:{e['id']}")] for e in events]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    return at(lang, "events_admin"), _kb(rows)


def _event_view(lang: str, event: dict) -> tuple[str, InlineKeyboardMarkup]:
    registered = f"{event['registered']}/{event['capacity']}" if event["capacity"] else str(event["registered"])
    text = at(
        lang,
        "ev_view",
        title=html.escape(event["title"]),
        when=content.format_dt(event["starts_at"]),
        place=_dash(event["place"]),
        registered=registered,
        notified=at(lang, "yes_sent") if event["notified"] else "—",
        desc=_dash(event["description"]),
    )
    eid = event["id"]
    markup = _kb(
        [
            [(at(lang, "btn_ev_list"), f"adm:evl:{eid}")],
            [(at(lang, "btn_ef_title"), f"adm:evf:{eid}:title"), (at(lang, "btn_ef_when"), f"adm:evf:{eid}:when")],
            [(at(lang, "btn_ef_place"), f"adm:evf:{eid}:place"), (at(lang, "btn_ef_desc"), f"adm:evf:{eid}:desc")],
            [(at(lang, "btn_ef_cap"), f"adm:evf:{eid}:cap")],
            [(at(lang, "btn_ev_notify"), f"adm:evn:{eid}")],
            [(at(lang, "btn_ev_delete"), f"adm:evd:{eid}")],
            [(at(lang, "btn_back"), "adm:ev")],
        ]
    )
    return text, markup


async def _gone(call: CallbackQuery, lang: str) -> None:
    await call.answer(at(lang, "ev_gone"), show_alert=True)
    text, markup = await _events_view(lang)
    await _edit(call, text, markup)


@admin_extra_router.callback_query(F.data == "adm:ev")
async def cb_events(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = await _events_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_extra_router.callback_query(F.data.startswith("adm:evv:"))
async def cb_event_view(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    await state.clear()
    await call.answer()
    text, markup = _event_view(lang, event)
    await _edit(call, text, markup)


# ---------- создание ----------

@admin_extra_router.callback_query(F.data == "adm:evnew")
async def cb_event_new(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    await state.clear()
    await state.set_state(EventCreate.title)
    await call.answer()
    await _edit(call, at(lang, "ev_ask_title"), _kb([[(at(lang, "btn_cancel"), "adm:ev")]]))


@admin_extra_router.message(EventCreate.title, *PLAIN_TEXT)
async def create_title(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("event_title", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(title=value)
    await state.set_state(EventCreate.when)
    await message.answer(at(lang, "ev_ask_when", example=_example_dt()))


def _check_future(timestamp: int | None) -> str | None:
    """Ключ ошибки или None, если дата подходит для мероприятия."""
    if timestamp is None:
        return "err_event_when"
    now = time.time()
    if timestamp <= now or timestamp > now + MAX_FUTURE_DAYS * 86400:
        return "err_event_when_past"
    return None


@admin_extra_router.message(EventCreate.when, *PLAIN_TEXT)
async def create_when(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    timestamp = content.parse_event_datetime(message.text or "")
    error = _check_future(timestamp)
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(when=timestamp)
    await state.set_state(EventCreate.place)
    await message.answer(at(lang, "ev_ask_place"))


@admin_extra_router.message(EventCreate.place, *PLAIN_TEXT)
async def create_place(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("event_place", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(place=value)
    await state.set_state(EventCreate.desc)
    await message.answer(at(lang, "ev_ask_desc"))


@admin_extra_router.message(EventCreate.desc, *PLAIN_TEXT)
async def create_desc(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("event_desc", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(desc=value)
    await state.set_state(EventCreate.cap)
    await message.answer(at(lang, "ev_ask_cap"))


@admin_extra_router.message(EventCreate.cap, *PLAIN_TEXT)
async def create_cap(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, capacity = content.validate_input("event_capacity", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    stored = await state.get_data()
    await state.clear()
    if not stored.get("title") or not stored.get("when"):
        return
    event_id = await db.add_event(stored["title"], stored.get("place", ""), stored.get("desc", ""), stored["when"], capacity)
    event = await db.get_event(event_id)
    text, markup = _event_view(lang, event)
    await message.answer(at(lang, "ev_saved") + "\n\n" + text, reply_markup=markup)


# ---------- редактирование ----------

_EDIT_FIELDS = {
    "title": ("event_title", "title"),
    "when": (None, "starts_at"),
    "place": ("event_place", "place"),
    "desc": ("event_desc", "description"),
    "cap": ("event_capacity", "capacity"),
}


@admin_extra_router.callback_query(F.data.startswith("adm:evf:"))
async def cb_event_edit(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    parts = (call.data or "").split(":")
    event_id = _int(parts[2]) if len(parts) == 4 else None
    field = parts[3] if len(parts) == 4 else ""
    if event_id is None or field not in _EDIT_FIELDS:
        await call.answer()
        return
    if await db.get_event(event_id) is None:
        await _gone(call, lang)
        return
    if field in ("title",):
        hint = at(lang, "hint_required")
    elif field == "when":
        hint = at(lang, "hint_when", example=_example_dt())
    else:
        hint = at(lang, "hint_optional")
    await state.clear()
    await state.set_state(EventEdit.value)
    await state.update_data(event_id=event_id, field=field)
    await call.answer()
    await _edit(
        call,
        at(lang, "ev_edit_ask", field=at(lang, f"f_ev_{field}"), hint=hint),
        _kb([[(at(lang, "btn_cancel"), f"adm:evv:{event_id}")]]),
    )


@admin_extra_router.message(EventEdit.value, *PLAIN_TEXT)
async def got_event_edit(message: Message, state: FSMContext, bot: Bot):
    lang = get_lang(message.from_user.id)
    stored = await state.get_data()
    event_id, field = stored.get("event_id"), stored.get("field")
    if not isinstance(event_id, int) or field not in _EDIT_FIELDS:
        await state.clear()
        return
    event = await db.get_event(event_id)
    if event is None:
        await state.clear()
        await message.answer(at(lang, "ev_gone"))
        return
    kind, db_field = _EDIT_FIELDS[field]
    if field == "when":
        value = content.parse_event_datetime(message.text or "")
        error = _check_future(value)
    else:
        error, value = content.validate_input(kind, message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await db.update_event(event_id, db_field, value)
    await state.clear()
    notice = at(lang, "ev_saved")
    if field in ("when", "place") and event["registered"] and event["starts_at"] > time.time():
        updated = await db.get_event(event_id)
        users = [r["user_id"] for r in await db.list_registrations(event_id)]
        await alerts.send_localized(
            bot, users, lambda l: (t(l, "event_changed", card=render_event(l, updated, with_count=False)), None)
        )
        notice += "\n" + at(lang, "ev_changed_notified")
    text, markup = _event_view(lang, await db.get_event(event_id))
    await message.answer(notice + "\n\n" + text, reply_markup=markup)


# ---------- список записавшихся ----------

@admin_extra_router.callback_query(F.data.startswith("adm:evl:"))
async def cb_event_regs(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    regs = await db.list_registrations(event_id)
    lines = []
    for i, reg in enumerate(regs[:60], 1):
        username = f" @{html.escape(reg['username'])}" if reg["username"] else ""
        lines.append(f"{i}. {html.escape(reg['name'] or '—')}{username}")
    if len(regs) > 60:
        lines.append(f"… +{len(regs) - 60}")
    text = at(lang, "reg_list_title", title=html.escape(event["title"]), count=len(regs), names="\n".join(lines) or at(lang, "reg_list_empty"))
    await call.answer()
    await _edit(call, text, _kb([[(at(lang, "btn_back"), f"adm:evv:{event_id}")]]))


# ---------- оповещение всех о мероприятии ----------

@admin_extra_router.callback_query(F.data.startswith("adm:evn:"))
async def cb_event_notify_ask(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    if event["notified"]:
        await call.answer(at(lang, "ev_notify_already"), show_alert=True)
        return
    count = len(await db.recipient_ids())
    await call.answer()
    await _edit(
        call,
        at(lang, "ev_notify_confirm", count=count, title=html.escape(event["title"])),
        _kb([[(at(lang, "btn_yes_send"), f"adm:evny:{event_id}"), (at(lang, "btn_cancel"), f"adm:evv:{event_id}")]]),
    )


@admin_extra_router.callback_query(F.data.startswith("adm:evny:"))
async def cb_event_notify_do(call: CallbackQuery, bot: Bot):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    if event["notified"]:
        await call.answer(at(lang, "ev_notify_already"), show_alert=True)
        return
    await db.set_event_notified(event_id)  # помечаем до отправки: повторное нажатие не создаст дубль
    await call.answer()
    await _edit(call, at(lang, "ev_notify_started"), _kb([[(at(lang, "btn_back"), f"adm:evv:{event_id}")]]))
    task = asyncio.create_task(_announce(bot, call.from_user.id, event_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _announce(bot: Bot, admin_id: int, event_id: int) -> None:
    event = await db.get_event(event_id)
    if event is None:
        return
    from events import open_event_inline

    stats = await alerts.send_localized(
        bot,
        await db.recipient_ids(),
        lambda l: (t(l, "event_announce", card=render_event(l, event, with_count=False)), open_event_inline(l, event_id)),
    )
    try:
        await bot.send_message(admin_id, at(get_lang(admin_id), "ev_notify_report", **stats))
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось отправить отчёт администратору %s", admin_id)


# ---------- удаление ----------

@admin_extra_router.callback_query(F.data.startswith("adm:evd:"))
async def cb_event_delete_ask(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    await call.answer()
    await _edit(
        call,
        at(lang, "ev_delete_confirm", title=html.escape(event["title"]), count=event["registered"]),
        _kb([[(at(lang, "btn_yes_send"), f"adm:evdy:{event_id}"), (at(lang, "btn_cancel"), f"adm:evv:{event_id}")]]),
    )


@admin_extra_router.callback_query(F.data.startswith("adm:evdy:"))
async def cb_event_delete_do(call: CallbackQuery, bot: Bot):
    lang = get_lang(call.from_user.id)
    event_id = _int((call.data or "").split(":")[-1])
    event = await db.get_event(event_id) if event_id is not None else None
    if event is None:
        await _gone(call, lang)
        return
    users = await db.delete_event(event_id)
    if users and event["starts_at"] > time.time():
        await alerts.send_localized(bot, users, lambda l: (t(l, "event_cancelled", title=html.escape(event["title"])), None))
    await call.answer(at(lang, "ev_deleted"))
    text, markup = await _events_view(lang)
    await _edit(call, text, markup)


# ======================================================================
# Обращения (предложения, жалобы, вопросы)
# ======================================================================

async def _inbox_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    items = await db.list_feedback()
    total = await db.count_feedback()
    rows = [
        [(f"№{f['id']} · {at(lang, 'kind_' + f['kind'])} · {f['text'].replace(chr(10), ' ')[:25]}"[:60], f"adm:fbv:{f['id']}")]
        for f in items
    ]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    return (at(lang, "fb_title", count=total) if items else at(lang, "fb_empty")), _kb(rows)


async def _inbox_gone(call: CallbackQuery, lang: str) -> None:
    await call.answer(at(lang, "fb_gone"), show_alert=True)
    text, markup = await _inbox_view(lang)
    await _edit(call, text, markup)


async def _open_feedback(raw: str) -> dict | None:
    fb_id = _int(raw)
    fb = await db.get_feedback(fb_id) if fb_id is not None else None
    return fb if fb is not None and fb["status"] == "new" else None


@admin_extra_router.callback_query(F.data == "adm:fb")
async def cb_inbox(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = await _inbox_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_extra_router.callback_query(F.data.startswith("adm:fbv:"))
async def cb_feedback_view(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    fb = await _open_feedback((call.data or "").split(":")[-1])
    if fb is None:
        await _inbox_gone(call, lang)
        return
    await state.clear()
    await call.answer()
    await _edit(call, alerts.feedback_text(lang, fb), alerts.feedback_markup(lang, fb["id"]))


@admin_extra_router.callback_query(F.data.startswith("adm:fbr:"))
async def cb_feedback_reply_ask(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    fb = await _open_feedback((call.data or "").split(":")[-1])
    if fb is None:
        await _inbox_gone(call, lang)
        return
    await state.clear()
    await state.set_state(FbReply.text)
    await state.update_data(fb_id=fb["id"])
    await call.answer()
    await _edit(call, at(lang, "fb_reply_ask", id=fb["id"]), _kb([[(at(lang, "btn_cancel"), f"adm:fbv:{fb['id']}")]]))


@admin_extra_router.message(FbReply.text, *PLAIN_TEXT)
async def got_feedback_reply(message: Message, state: FSMContext, bot: Bot):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("reply_text", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    fb_id = (await state.get_data()).get("fb_id")
    fb = await _open_feedback(str(fb_id)) if isinstance(fb_id, int) else None
    await state.clear()
    if fb is None:
        text, markup = await _inbox_view(lang)
        await message.answer(at(lang, "fb_gone") + "\n\n" + text, reply_markup=markup)
        return
    user_lang = get_lang(fb["user_id"])
    delivered = True
    try:
        await bot.send_message(fb["user_id"], t(user_lang, "fb_reply", id=fb["id"], reply=html.escape(value)))
    except TelegramForbiddenError:
        delivered = False
        await db.mark_blocked(fb["user_id"])
    except Exception:  # noqa: BLE001
        delivered = False
        logger.exception("Не удалось отправить ответ на обращение %s", fb["id"])
    if delivered:
        await db.set_feedback_status(fb["id"], "answered")
    text, markup = await _inbox_view(lang)
    await message.answer(at(lang, "fb_reply_sent" if delivered else "fb_reply_failed") + "\n\n" + text, reply_markup=markup)


@admin_extra_router.callback_query(F.data.startswith("adm:fbc:"))
async def cb_feedback_close(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    fb = await _open_feedback((call.data or "").split(":")[-1])
    if fb is None or not await db.set_feedback_status(fb["id"], "closed"):
        await _inbox_gone(call, lang)
        return
    await call.answer(at(lang, "fb_closed"))
    text, markup = await _inbox_view(lang)
    await _edit(call, text, markup)


@admin_extra_router.callback_query(F.data.startswith("adm:fbm:"))
async def cb_feedback_mute(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    fb = await _open_feedback((call.data or "").split(":")[-1])
    if fb is None:
        await _inbox_gone(call, lang)
        return
    await db.mute_user(fb["user_id"], int(time.time()) + MUTE_DAYS * 86400)
    await db.set_feedback_status(fb["id"], "closed")
    await call.answer(at(lang, "fb_muted_done"), show_alert=True)
    text, markup = await _inbox_view(lang)
    await _edit(call, text, markup)