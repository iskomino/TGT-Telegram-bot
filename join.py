"""Заявка в клуб: имя -> факультет -> телефон (необязательно) -> подтверждение -> уведомление админам."""
import html

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import alerts
import content
import data
import db
import keyboards as kb
from flows import PLAIN_TEXT, cancel_markup, stray_input
from store import get_lang
from texts import t

join_router = Router(name="join")
join_router.message.filter(F.chat.type == "private")


class Join(StatesGroup):
    name = State()
    faculty = State()
    phone = State()
    confirm = State()


def _club(slug: str | None):
    return next((c for c in data.CLUBS if c["slug"] == slug), None)


@join_router.callback_query(F.data == "join:send", StateFilter(Join.confirm))
async def cb_join_send(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    stored = await state.get_data()
    await state.clear()
    await call.answer()
    club = _club(stored.get("club"))
    if club is None or not stored.get("name") or not stored.get("faculty"):
        return
    app_id, error = await db.add_application(
        club["slug"], call.from_user.id, stored["name"], stored["faculty"], stored.get("phone", ""), call.from_user.username or ""
    )
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass
        if error:
            await call.message.answer(t(lang, "join_duplicate" if error == "duplicate" else "join_limit"), reply_markup=kb.main_menu(lang))
            return
        await alerts.alert_new_application(call.bot, app_id)
        await call.message.answer(t(lang, "join_done", id=app_id), reply_markup=kb.main_menu(lang))


@join_router.callback_query(F.data.startswith("join:"))
async def cb_join(call: CallbackQuery, state: FSMContext):
    raw = (call.data or "").split(":", 1)[-1]
    if not raw.isdigit() or int(raw) >= len(data.CLUBS):
        await call.answer()
        return
    club = data.CLUBS[int(raw)]
    lang = get_lang(call.from_user.id)
    error = await db.application_precheck(call.from_user.id, club["slug"])
    if error:
        await call.answer(t(lang, "join_duplicate" if error == "duplicate" else "join_limit"), show_alert=True)
        return
    await state.clear()
    await state.set_state(Join.name)
    await state.update_data(club=club["slug"])
    await call.answer()
    if isinstance(call.message, Message):
        await call.message.answer(t(lang, "join_intro", club=html.escape(club["name"][lang])), reply_markup=cancel_markup(lang))


@join_router.message(Join.name, *PLAIN_TEXT)
async def got_name(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("app_name", message.text or "")
    if error:
        await message.answer(t(lang, error), reply_markup=cancel_markup(lang))
        return
    await state.update_data(name=value)
    await state.set_state(Join.faculty)
    await message.answer(t(lang, "join_ask_faculty"), reply_markup=cancel_markup(lang))


@join_router.message(Join.faculty, *PLAIN_TEXT)
async def got_faculty(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("app_faculty", message.text or "")
    if error:
        await message.answer(t(lang, error), reply_markup=cancel_markup(lang))
        return
    await state.update_data(faculty=value)
    await state.set_state(Join.phone)
    await message.answer(t(lang, "join_ask_phone"), reply_markup=cancel_markup(lang))


@join_router.message(Join.phone, *PLAIN_TEXT)
async def got_phone(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("app_phone", message.text or "")
    if error:
        await message.answer(t(lang, error), reply_markup=cancel_markup(lang))
        return
    await state.update_data(phone=value)
    await state.set_state(Join.confirm)
    stored = await state.get_data()
    club = _club(stored.get("club"))
    if club is None:
        await state.clear()
        return
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_send"), callback_data="join:send"),
                InlineKeyboardButton(text=t(lang, "btn_cancel_inline"), callback_data="flow:cancel"),
            ]
        ]
    )
    await message.answer(
        t(
            lang,
            "join_confirm",
            club=html.escape(club["name"][lang]),
            name=html.escape(stored["name"]),
            faculty=html.escape(stored["faculty"]),
            phone=html.escape(value) if value else "—",
        ),
        reply_markup=markup,
    )


@join_router.message(StateFilter(Join.name, Join.faculty, Join.phone), stray_input)
async def join_non_text(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "only_text"), reply_markup=cancel_markup(lang))
