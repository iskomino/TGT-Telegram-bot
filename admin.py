"""Админ-панель внутри бота (/admin). Доступна только пользователям из ADMIN_IDS (.env).

Возможности: статистика, рассылка, редактирование клубов (описание, сədr и müavin), команды TGT
(İdarə Heyəti: 7 мест — имя, фамилия, отчество, должность, телефон, e-mail) и информации о TGT (комната, адрес, текст).
Язык панели совпадает с языком, выбранным администратором в боте; тексты в admin_texts.py.
"""
import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import content
import data
import db
from admin_texts import AT, at
from config import ADMIN_IDS
from store import get_lang
from texts import ALL_REPLY_BUTTONS

logger = logging.getLogger(__name__)

admin_router = Router(name="admin")
admin_router.message.filter(F.chat.type == "private", F.from_user.id.in_(ADMIN_IDS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

MAX_BROADCAST_LEN = 3500
INFO_FIELDS = ("room", "address", "about")
_tasks: set[asyncio.Task] = set()

# Обычный текст пользователя (не команда и не кнопка меню)
_PLAIN_TEXT = (F.text, ~F.text.startswith("/"), ~F.text.in_(ALL_REPLY_BUTTONS))


class Broadcast(StatesGroup):
    text = State()
    confirm = State()


class EditField(StatesGroup):
    value = State()


class EditDesc(StatesGroup):
    value = State()


class EditInfo(StatesGroup):
    value = State()


def _kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows]
    )


def _club_index(raw: str) -> int | None:
    return int(raw) if raw.isdigit() and int(raw) < len(data.CLUBS) else None


async def _edit(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


def _dash(value: str) -> str:
    return html.escape(value) if value else "—"


# ---------- Панель ----------

async def panel_kb(lang: str) -> InlineKeyboardMarkup:
    """Главная панель; на кнопках разделов показываются счётчики (открытые заявки, обращения, ближайшие события)."""

    def label(key: str, count: int) -> str:
        return f"{at(lang, key)} ({count})" if count else at(lang, key)

    apps = await db.count_applications()
    inbox = await db.count_feedback()
    events = await db.count_upcoming_events()
    return _kb(
        [
            [(at(lang, "btn_stats"), "adm:stats")],
            [(at(lang, "btn_broadcast"), "adm:bc")],
            [(at(lang, "btn_clubs"), "adm:clubs")],
            [(at(lang, "btn_team"), "adm:team")],
            [(at(lang, "btn_info"), "adm:info")],
            [(label("btn_events", events), "adm:ev")],
            [(at(lang, "btn_news"), "adm:nw")],
            [(at(lang, "btn_faq"), "adm:fq")],
            [(label("btn_apps", apps), "adm:ap")],
            [(label("btn_inbox", inbox), "adm:fb")],
        ]
    )


def home_kb(lang: str) -> InlineKeyboardMarkup:
    return _kb([[(at(lang, "btn_home"), "adm:home")]])


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    lang = get_lang(message.from_user.id)
    await message.answer(at(lang, "panel"), reply_markup=await panel_kb(lang))


@admin_router.callback_query(F.data == "adm:home")
async def cb_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    lang = get_lang(call.from_user.id)
    await _edit(call, at(lang, "panel"), await panel_kb(lang))


# ---------- Статистика ----------

def _section_label(lang: str, section: str, faq_titles: dict | None = None) -> str:
    if section.startswith("faq.") and section[4:].isdigit():
        title = (faq_titles or {}).get(int(section[4:]))
        return f"❓ {title[:40]}" if title else "❓ …"
    if section == "quiz":
        return at(lang, "sec_quiz")
    if section.startswith("quiz."):
        club = next((c for c in data.CLUBS if c["slug"] == section[len("quiz."):]), None)
        if club:
            return f"🧩 {at(lang, 'sec_quiz_result')}: {club['name'][lang]}"
    if section.startswith("club."):
        club = next((c for c in data.CLUBS if c["slug"] == section[len("club."):]), None)
        if club:
            return f"{club['emoji']} {club['name'][lang]}"
    return AT.get(lang, AT["az"]).get(f"sec_{section}", section)


@admin_router.callback_query(F.data == "adm:stats")
async def cb_stats(call: CallbackQuery):
    await call.answer()
    lang = get_lang(call.from_user.id)
    s = await db.get_stats()
    langs = " · ".join(f"{code} {cnt}" for code, cnt in sorted(s["langs"].items())) or "—"
    faq_ids = [int(sec[4:]) for sec, _ in s["top_sections"] if sec.startswith("faq.") and sec[4:].isdigit()]
    faq_titles = await db.faq_questions(faq_ids)
    top = "\n".join(f"• {html.escape(_section_label(lang, sec, faq_titles))}: {cnt}" for sec, cnt in s["top_sections"])
    text = at(
        lang,
        "stats",
        total=s["total"],
        a24=s["active_24h"],
        a7=s["active_7d"],
        blocked=s["blocked"],
        langs=html.escape(langs),
        top=top or at(lang, "no_data"),
    )
    await _edit(call, text, home_kb(lang))


# ---------- Рассылка ----------

@admin_router.callback_query(F.data == "adm:bc")
async def cb_bc(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    await state.set_state(Broadcast.text)
    await call.answer()
    await _edit(call, at(lang, "bc_prompt", max=MAX_BROADCAST_LEN), _kb([[(at(lang, "btn_cancel"), "adm:home")]]))


@admin_router.message(Broadcast.text, *_PLAIN_TEXT)
async def got_broadcast_text(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    text = (message.text or "").strip()
    if not text or len(text) > MAX_BROADCAST_LEN:
        await message.answer(at(lang, "bc_bad_length", max=MAX_BROADCAST_LEN))
        return
    await state.update_data(text=text)
    await state.set_state(Broadcast.confirm)
    count = len(await db.recipient_ids())
    await message.answer(
        at(lang, "bc_preview", count=count, text=text),
        parse_mode=None,
        reply_markup=_kb([[(at(lang, "btn_send_all"), "adm:bc_send"), (at(lang, "btn_cancel"), "adm:home")]]),
    )


@admin_router.callback_query(F.data == "adm:bc_send", StateFilter(Broadcast.confirm))
async def cb_bc_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    lang = get_lang(call.from_user.id)
    text = (await state.get_data()).get("text")
    await state.clear()
    await call.answer()
    if not text:
        return
    await _edit(call, at(lang, "bc_started"), None)
    task = asyncio.create_task(_broadcast(bot, call.from_user.id, text))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _broadcast(bot: Bot, admin_id: int, text: str) -> None:
    sent = blocked = failed = 0
    for uid in await db.recipient_ids():
        try:
            await bot.send_message(uid, text, parse_mode=None)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await bot.send_message(uid, text, parse_mode=None)
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
        except TelegramForbiddenError:
            blocked += 1
            await db.mark_blocked(uid)
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить рассылку пользователю %s", uid)
            failed += 1
        await asyncio.sleep(0.05)  # ~20 сообщений/с, ниже лимита Telegram
    try:
        await bot.send_message(admin_id, at(get_lang(admin_id), "bc_report", sent=sent, blocked=blocked, failed=failed))
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось отправить отчёт о рассылке администратору %s", admin_id)


# ---------- Люди: общий редактор (сədr/müavin клуба и места команды) ----------

def _person_title(lang: str, key: str) -> str:
    kind, index, which = content.parse_key(key)
    if kind == "club":
        role = at(lang, "role_chair" if which == "chair" else "role_deputy")
        return f"{data.CLUBS[index]['name'][lang]} · {role}"
    return at(lang, "slot_title", n=index + 1)


def _back_target(key: str) -> str:
    kind, index, _ = content.parse_key(key)
    return f"adm:club:{index}" if kind == "club" else "adm:team"


def _person_view(lang: str, key: str) -> tuple[str, InlineKeyboardMarkup]:
    person = content.get_person(key)
    fields = content.fields_for(key)
    lines = "\n".join(f"{at(lang, 'f_' + f)}: {_dash(person[f])}" for f in fields)
    buttons = [(at(lang, f"f_{f}"), f"adm:pf:{key}:{f}") for f in fields]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([(at(lang, "btn_clear"), f"adm:pc:{key}")])
    rows.append([(at(lang, "btn_back"), _back_target(key))])
    text = at(lang, "person_screen", title=html.escape(_person_title(lang, key)), fields=lines)
    return text, _kb(rows)


@admin_router.callback_query(F.data.startswith("adm:pe:"))
async def cb_person(call: CallbackQuery, state: FSMContext):
    key = (call.data or "").split(":", 2)[-1]
    if content.parse_key(key) is None:
        await call.answer()
        return
    await state.clear()
    await call.answer()
    text, markup = _person_view(get_lang(call.from_user.id), key)
    await _edit(call, text, markup)


@admin_router.callback_query(F.data.startswith("adm:pf:"))
async def cb_field(call: CallbackQuery, state: FSMContext):
    parts = (call.data or "").split(":")
    key, field = (parts[2], parts[3]) if len(parts) == 4 else ("", "")
    if content.parse_key(key) is None or field not in content.fields_for(key):
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await state.set_state(EditField.value)
    await state.update_data(key=key, field=field)
    await call.answer()
    await _edit(
        call,
        at(lang, "ask_field", title=html.escape(_person_title(lang, key)), field=at(lang, f"f_{field}")),
        _kb([[(at(lang, "btn_cancel"), f"adm:pe:{key}")]]),
    )


@admin_router.message(EditField.value, *_PLAIN_TEXT)
async def got_field(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    stored = await state.get_data()
    key, field = stored.get("key") or "", stored.get("field") or ""
    if content.parse_key(key) is None or field not in content.fields_for(key):
        await state.clear()
        return
    error, value = content.validate(field, message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await content.save_person_field(key, field, value)
    await state.clear()
    text, markup = _person_view(lang, key)
    await message.answer(at(lang, "saved") + "\n\n" + text, reply_markup=markup)


@admin_router.callback_query(F.data.startswith("adm:pc:"))
async def cb_clear_ask(call: CallbackQuery, state: FSMContext):
    key = (call.data or "").split(":", 2)[-1]
    if content.parse_key(key) is None:
        await call.answer()
        return
    await state.clear()
    await call.answer()
    lang = get_lang(call.from_user.id)
    await _edit(
        call,
        at(lang, "clear_confirm", title=html.escape(_person_title(lang, key))),
        _kb([[(at(lang, "btn_yes_clear"), f"adm:pcy:{key}"), (at(lang, "btn_cancel"), f"adm:pe:{key}")]]),
    )


@admin_router.callback_query(F.data.startswith("adm:pcy:"))
async def cb_clear_do(call: CallbackQuery):
    key = (call.data or "").split(":", 2)[-1]
    if content.parse_key(key) is None:
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await content.clear_person(key)
    await call.answer(at(lang, "cleared"))
    text, markup = _person_view(lang, key)
    await _edit(call, text, markup)


# ---------- Клубы ----------

@admin_router.callback_query(F.data == "adm:clubs")
async def cb_clubs(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    lang = get_lang(call.from_user.id)
    rows = [[(f"{c['emoji']} {c['name'][lang]}", f"adm:club:{i}")] for i, c in enumerate(data.CLUBS)]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    await _edit(call, at(lang, "clubs_title"), _kb(rows))


def _person_summary(person: dict[str, str]) -> str:
    if not content.is_filled(person):
        return "—"
    phone = f" · {html.escape(person['phone'])}" if person["phone"] else ""
    return html.escape(content.full_name(person)) + phone


def _club_view(lang: str, index: int) -> tuple[str, InlineKeyboardMarkup]:
    club = data.CLUBS[index]
    slug = club["slug"]
    text = at(
        lang,
        "club_screen",
        name=html.escape(club["name"][lang]),
        desc=html.escape(content.get_description(slug, lang)),
        chair_role=at(lang, "role_chair"),
        chair=_person_summary(content.get_person(content.club_person_key(slug, "chair"))),
        deputy_role=at(lang, "role_deputy"),
        deputy=_person_summary(content.get_person(content.club_person_key(slug, "deputy"))),
    )
    markup = _kb(
        [
            [(at(lang, "btn_chair"), f"adm:pe:{content.club_person_key(slug, 'chair')}"),
             (at(lang, "btn_deputy"), f"adm:pe:{content.club_person_key(slug, 'deputy')}")],
            [(at(lang, "btn_desc"), f"adm:cd:{index}")],
            [(at(lang, "btn_desc_reset"), f"adm:cdr:{index}")],
            [(at(lang, "btn_back"), "adm:clubs")],
        ]
    )
    return text, markup


@admin_router.callback_query(F.data.startswith("adm:club:"))
async def cb_club(call: CallbackQuery, state: FSMContext):
    index = _club_index((call.data or "").split(":", 2)[-1])
    if index is None:
        await call.answer()
        return
    await state.clear()
    await call.answer()
    text, markup = _club_view(get_lang(call.from_user.id), index)
    await _edit(call, text, markup)


@admin_router.callback_query(F.data.startswith("adm:cd:"))
async def cb_desc_ask(call: CallbackQuery, state: FSMContext):
    index = _club_index((call.data or "").split(":", 2)[-1])
    if index is None:
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await state.set_state(EditDesc.value)
    await state.update_data(club=index)
    await call.answer()
    await _edit(
        call,
        at(lang, "ask_desc", name=html.escape(data.CLUBS[index]["name"][lang]), min=content.TEXT_MIN, max=content.TEXT_MAX),
        _kb([[(at(lang, "btn_cancel"), f"adm:club:{index}")]]),
    )


@admin_router.message(EditDesc.value, *_PLAIN_TEXT)
async def got_desc(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    index = (await state.get_data()).get("club")
    if not isinstance(index, int) or not 0 <= index < len(data.CLUBS):
        await state.clear()
        return
    error, value = content.validate("desc", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    slug = data.CLUBS[index]["slug"]
    if value:
        await content.set_description(slug, value)
        notice = at(lang, "saved")
    else:  # «-» возвращает стандартное описание
        await content.reset_description(slug)
        notice = at(lang, "desc_reset_done")
    await state.clear()
    text, markup = _club_view(lang, index)
    await message.answer(notice + "\n\n" + text, reply_markup=markup)


@admin_router.callback_query(F.data.startswith("adm:cdr:"))
async def cb_desc_reset(call: CallbackQuery, state: FSMContext):
    index = _club_index((call.data or "").split(":", 2)[-1])
    if index is None:
        await call.answer()
        return
    await state.clear()
    lang = get_lang(call.from_user.id)
    await content.reset_description(data.CLUBS[index]["slug"])
    await call.answer(at(lang, "desc_reset_done"))
    text, markup = _club_view(lang, index)
    await _edit(call, text, markup)


# ---------- Команда TGT ----------

@admin_router.callback_query(F.data == "adm:team")
async def cb_team(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    lang = get_lang(call.from_user.id)
    rows = []
    for slot in range(data.TEAM_SLOTS):
        person = content.get_person(content.team_person_key(slot))
        if content.is_filled(person):
            label = f"{slot + 1}. {content.full_name(person)} · {person['role'] or '—'}"
        else:
            label = f"{slot + 1}. —"
        rows.append([(label[:60], f"adm:pe:{content.team_person_key(slot)}")])
    rows.append([(at(lang, "btn_home"), "adm:home")])
    await _edit(call, at(lang, "team_title"), _kb(rows))


# ---------- Информация о TGT ----------

def _info_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    text = at(
        lang,
        "info_screen",
        room=_dash(content.get_room()),
        address=_dash(content.get_address()),
        about=html.escape(content.get_about(lang)),
    )
    markup = _kb(
        [
            [(at(lang, "btn_room"), "adm:if:room"), (at(lang, "btn_address"), "adm:if:address")],
            [(at(lang, "btn_about_text"), "adm:if:about")],
            [(at(lang, "btn_home"), "adm:home")],
        ]
    )
    return text, markup


@admin_router.callback_query(F.data == "adm:info")
async def cb_info(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = _info_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_router.callback_query(F.data.startswith("adm:if:"))
async def cb_info_ask(call: CallbackQuery, state: FSMContext):
    field = (call.data or "").split(":", 2)[-1]
    if field not in INFO_FIELDS:
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await state.set_state(EditInfo.value)
    await state.update_data(field=field)
    await call.answer()
    if field == "about":
        prompt = at(lang, "ask_info_reset", field=at(lang, "f_about"), min=content.TEXT_MIN, max=content.TEXT_MAX)
    else:
        prompt = at(lang, "ask_info_clear", field=at(lang, f"f_{field}"))
    await _edit(call, prompt, _kb([[(at(lang, "btn_cancel"), "adm:info")]]))


@admin_router.message(EditInfo.value, *_PLAIN_TEXT)
async def got_info(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    field = (await state.get_data()).get("field")
    if field not in INFO_FIELDS:
        await state.clear()
        return
    error, value = content.validate(field, message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await content.set_info(field, value)
    await state.clear()
    text, markup = _info_view(lang)
    await message.answer(at(lang, "saved") + "\n\n" + text, reply_markup=markup)


# ---------- Устаревшие кнопки ----------

@admin_router.callback_query(F.data.startswith("adm:"))
async def cb_stale(call: CallbackQuery):
    await call.answer(at(get_lang(call.from_user.id), "stale"), show_alert=False)
