import html
import logging
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message

import content
import data
import db
import keyboards as kb
from config import ADMIN_IDS, DEVELOPER_CONTACT, DEVELOPER_NAME
from store import USER_LANG, get_lang
from texts import LANGS, T, t

logger = logging.getLogger(__name__)
router = Router(name="main")
router.message.filter(F.chat.type == "private")


def is_btn(key: str):
    """Фильтр: текст сообщения совпадает с кнопкой `key` на любом из языков."""
    return F.text.in_({T[lang][key] for lang in T})


# ---------- Оформление карточек ----------

def _contact_lines(person: dict[str, str]) -> list[str]:
    lines = []
    if person.get("phone"):
        lines.append(f"☎️ {html.escape(person['phone'])}")
    if person.get("email"):
        lines.append(f"✉️ {html.escape(person['email'])}")
    return lines


def _club_person_block(lang: str, person: dict[str, str], role_label: str) -> str:
    if not content.is_filled(person):
        return f"👤 <b>{html.escape(role_label)}:</b> {t(lang, 'vacant')}"
    lines = [f"👤 <b>{html.escape(role_label)}:</b> {html.escape(content.full_name(person))}"]
    return "\n".join(lines + _contact_lines(person))


def _team_block(lang: str, person: dict[str, str]) -> str:
    role = content.localized_role(person.get("role", ""), lang) or t(lang, "role_member")
    lines = [f"👤 <b>{html.escape(role)}</b>", html.escape(content.full_name(person))]
    return "\n".join(lines + _contact_lines(person))


def render_club(lang: str, index: int) -> str:
    club = data.CLUBS[index]
    slug = club["slug"]
    people = [
        _club_person_block(lang, content.get_person(content.club_person_key(slug, "chair")), t(lang, "role_chair")),
        _club_person_block(lang, content.get_person(content.club_person_key(slug, "deputy")), t(lang, "role_deputy")),
    ]
    return (
        f"{club['emoji']} <b>{html.escape(club['name'][lang])}</b>\n\n"
        f"{html.escape(content.get_description(slug, lang))}\n\n" + "\n\n".join(people)
    )


def render_about(lang: str) -> str:
    parts = [t(lang, "about_header"), html.escape(content.get_about(lang))]
    head = content.get_person(content.team_person_key(0))  # в «О TGT» показывается только руководитель
    if content.is_filled(head):
        parts.append(_team_block(lang, head))
    tail = []
    if content.get_address():
        tail.append(t(lang, "address_line", address=html.escape(content.get_address())))
    if content.get_room():
        tail.append(t(lang, "room_line", room=html.escape(content.get_room())))
    if tail:
        parts.append("\n".join(tail))
    credit = developer_line(lang)
    if credit:
        parts.append(credit)
    return "\n\n".join(parts)


def developer_line(lang: str) -> str:
    """Подпись разработчика; пустая строка, если имя не задано. @username превращается в ссылку на Telegram."""
    if not DEVELOPER_NAME:
        return ""
    line = t(lang, "developer_line", name=html.escape(DEVELOPER_NAME))
    contact = DEVELOPER_CONTACT
    if contact:
        if re.fullmatch(r"@[A-Za-z0-9_]{4,32}", contact):
            line += f' · <a href="https://t.me/{contact[1:]}">{html.escape(contact)}</a>'
        else:
            line += f" · {html.escape(contact)}"
    return line


def render_board(lang: str) -> str:
    parts = [t(lang, "board_header")]
    for slot in range(data.TEAM_SLOTS):  # пустые места пользователям не показываются
        person = content.get_person(content.team_person_key(slot))
        if content.is_filled(person):
            parts.append(_team_block(lang, person))
    if len(parts) == 1:
        parts.append(t(lang, "board_empty"))
    return "\n\n".join(parts)


# ---------- Старт, язык, меню ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    uid = message.from_user.id
    if uid not in USER_LANG:
        await message.answer(T["az"]["choose_lang"], reply_markup=kb.language_inline())
        return
    lang = get_lang(uid)
    await message.answer(t(lang, "welcome"), reply_markup=kb.main_menu(lang))


@router.message(Command("menu"))
async def show_menu(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "menu_title"), reply_markup=kb.main_menu(lang))


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    credit = developer_line(lang)
    await message.answer(t(lang, "help") + (f"\n\n{credit}" if credit else ""), reply_markup=kb.main_menu(lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "cancelled"), reply_markup=kb.main_menu(lang))


@router.message(is_btn("btn_lang"))
async def change_lang(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(T["az"]["choose_lang"], reply_markup=kb.language_inline())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery, state: FSMContext):
    code = (call.data or "").split(":", 1)[-1]
    if code not in LANGS:
        await call.answer()
        return
    USER_LANG[call.from_user.id] = code
    try:
        await db.set_lang(call.from_user.id, code)
    except Exception:  # noqa: BLE001 - язык остаётся в памяти, бот продолжает работать
        logger.exception("Не удалось сохранить язык пользователя")
    await state.clear()
    await call.answer()
    if isinstance(call.message, Message):
        try:
            await call.message.delete()
        except TelegramBadRequest:
            pass
        await call.message.answer(t(code, "welcome"), reply_markup=kb.main_menu(code))


# ---------- Клубы ----------

@router.message(is_btn("btn_clubs"))
async def clubs(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "clubs_title"), reply_markup=kb.clubs_inline(lang))


@router.callback_query(F.data.startswith("club:"))
async def cb_club(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    raw = (call.data or "").split(":", 1)[-1]
    if raw == "list":
        text, markup = t(lang, "clubs_title"), kb.clubs_inline(lang)
    else:
        if not raw.isdigit() or int(raw) >= len(data.CLUBS):
            await call.answer()
            return
        index = int(raw)
        text, markup = render_club(lang, index), kb.club_back_inline(lang, index)
        try:  # статистика просмотров клубов
            await db.log_event(f"club.{data.CLUBS[index]['slug']}")
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось записать просмотр клуба")
    await call.answer()
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


# ---------- О TGT ----------

@router.message(is_btn("btn_about"))
async def about(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(render_about(lang), reply_markup=kb.main_menu(lang))
    await message.answer_location(latitude=data.UNIVERSITY_LAT, longitude=data.UNIVERSITY_LON)


# ---------- İdarə Heyəti (Правление) ----------

@router.message(is_btn("btn_board"))
async def board(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(render_board(lang), reply_markup=kb.main_menu(lang))


# ---------- Прочее ----------

@router.message()
async def fallback(message: Message):
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "unknown"), reply_markup=kb.main_menu(lang))


@router.error()
async def on_error(event: ErrorEvent, bot: Bot):
    logger.exception("Unhandled error", exc_info=event.exception)
    text = f"⚠️ Bot error: <code>{html.escape(repr(event.exception))[:500]}</code>"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:  # noqa: BLE001 - уведомление не должно ломать бота
            logger.warning("Could not notify admin %s", admin_id)
    return True
