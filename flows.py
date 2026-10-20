"""Общие части пошаговых диалогов (заявка в клуб, обращение): фильтры ввода и кнопка отмены."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import keyboards as kb
from store import get_lang
from texts import ALL_REPLY_BUTTONS, T, t

# Обычный текст пользователя: не команда и не кнопка меню (иначе кнопка меню стала бы «ответом» в диалоге)
PLAIN_TEXT = (F.text, ~F.text.startswith("/"), ~F.text.in_(ALL_REPLY_BUTTONS))


def is_btn(key: str):
    """Фильтр: текст сообщения совпадает с кнопкой `key` на любом из языков."""
    return F.text.in_({T[lang][key] for lang in T})


async def stray_input(message: Message) -> bool:
    """Любое сообщение, кроме команд и кнопок меню (стикеры, фото, голосовые и т.п.)."""
    text = message.text
    return not (text and (text.startswith("/") or text in ALL_REPLY_BUTTONS))


def cancel_markup(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_cancel_inline"), callback_data="flow:cancel")]]
    )


flow_router = Router(name="flow")
flow_router.message.filter(F.chat.type == "private")


@flow_router.callback_query(F.data == "flow:cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    lang = get_lang(call.from_user.id)
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await call.message.answer(t(lang, "cancelled"), reply_markup=kb.main_menu(lang))
