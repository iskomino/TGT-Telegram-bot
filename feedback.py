"""Ящик обращений: тип (предложение / жалоба / вопрос) -> анонимно или с именем -> текст -> администраторам."""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import alerts
import content
import db
import keyboards as kb
from flows import PLAIN_TEXT, cancel_markup, is_btn, stray_input
from store import get_lang
from texts import t

feedback_router = Router(name="feedback")
feedback_router.message.filter(F.chat.type == "private")

KINDS = ("s", "c", "q")  # suggestion / complaint / question


class Feedback(StatesGroup):
    text = State()


def _kind_markup(lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t(lang, f"kind_{k}"), callback_data=f"fb:k:{k}")] for k in KINDS]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_cancel_inline"), callback_data="flow:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _anon_markup(lang: str, kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_named"), callback_data=f"fb:a:{kind}:0")],
            [InlineKeyboardButton(text=t(lang, "btn_anon"), callback_data=f"fb:a:{kind}:1")],
            [InlineKeyboardButton(text=t(lang, "btn_cancel_inline"), callback_data="flow:cancel")],
        ]
    )


@feedback_router.message(is_btn("btn_feedback"))
async def feedback_menu(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    if await db.is_muted(message.from_user.id):
        await message.answer(t(lang, "fb_muted"), reply_markup=kb.main_menu(lang))
        return
    await message.answer(t(lang, "fb_intro"), reply_markup=_kind_markup(lang))


@feedback_router.callback_query(F.data.startswith("fb:k:"))
async def cb_kind(call: CallbackQuery):
    kind = (call.data or "").split(":")[-1]
    if kind not in KINDS:
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await call.answer()
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(t(lang, "fb_ask_anon"), reply_markup=_anon_markup(lang, kind))
        except Exception:  # noqa: BLE001
            pass


@feedback_router.callback_query(F.data.startswith("fb:a:"))
async def cb_anon(call: CallbackQuery, state: FSMContext):
    parts = (call.data or "").split(":")
    if len(parts) != 4 or parts[2] not in KINDS or parts[3] not in ("0", "1"):
        await call.answer()
        return
    lang = get_lang(call.from_user.id)
    await state.clear()
    await state.set_state(Feedback.text)
    await state.update_data(kind=parts[2], anonymous=parts[3] == "1")
    await call.answer()
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass
        await call.message.answer(t(lang, "fb_ask_text"), reply_markup=cancel_markup(lang))


@feedback_router.message(Feedback.text, *PLAIN_TEXT)
async def got_text(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_input("fb_text", message.text or "")
    if error:
        await message.answer(t(lang, error), reply_markup=cancel_markup(lang))
        return
    stored = await state.get_data()
    kind = stored.get("kind")
    if kind not in KINDS:
        await state.clear()
        return
    user = message.from_user
    fb_id, problem = await db.add_feedback(
        user.id, kind, bool(stored.get("anonymous")), (user.full_name or "")[:60], user.username or "", value
    )
    if problem == "cooldown":  # текст не теряем: можно отправить ещё раз через пару секунд
        await message.answer(t(lang, "fb_cooldown"), reply_markup=cancel_markup(lang))
        return
    await state.clear()
    if problem:
        await message.answer(t(lang, "fb_muted" if problem == "muted" else "fb_limit"), reply_markup=kb.main_menu(lang))
        return
    await alerts.alert_new_feedback(message.bot, fb_id)
    await message.answer(t(lang, "fb_done", id=fb_id), reply_markup=kb.main_menu(lang))


@feedback_router.message(StateFilter(Feedback.text), stray_input)
async def feedback_non_text(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "only_text"), reply_markup=cancel_markup(lang))
