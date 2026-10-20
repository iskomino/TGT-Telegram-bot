"""FAQ для студентов: список вопросов (без номеров, по страницам) и карточка с ответом."""
import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import content
import db
from flows import is_btn
from store import get_lang
from texts import t

logger = logging.getLogger(__name__)

faq_router = Router(name="faq")
faq_router.message.filter(F.chat.type == "private")

FAQ_PAGE = 8  # вопросов на странице


def render_card(lang: str, item: dict) -> str:
    question, answer = content.faq_text(item, lang)
    return f"❓ <b>{html.escape(question)}</b>\n\n{html.escape(answer)}"


def _button_text(question: str) -> str:
    return question if len(question) <= 58 else question[:57] + "…"


def _pages(count: int) -> int:
    return max(1, -(-count // FAQ_PAGE))


def list_view(lang: str, items: list[dict], page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    if not items:
        return t(lang, "faq_empty"), None
    page = min(max(page, 0), _pages(len(items)) - 1)
    rows = [
        [InlineKeyboardButton(text=_button_text(content.faq_text(item, lang)[0]), callback_data=f"faq:{item['id']}:{page}")]
        for item in items[page * FAQ_PAGE : (page + 1) * FAQ_PAGE]
    ]
    pages = _pages(len(items))
    if pages > 1:
        rows.append(
            [
                InlineKeyboardButton(text="◀️", callback_data=f"faq:p:{max(page - 1, 0)}"),
                InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data=f"faq:p:{page}"),
                InlineKeyboardButton(text="▶️", callback_data=f"faq:p:{min(page + 1, pages - 1)}"),
            ]
        )
    return t(lang, "faq_title"), InlineKeyboardMarkup(inline_keyboard=rows)


async def _edit(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


@faq_router.message(is_btn("btn_faq"))
async def faq_menu(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    text, markup = list_view(lang, await db.list_faq(), 0)
    await message.answer(text, reply_markup=markup)


@faq_router.callback_query(F.data.regexp(r"^faq:p:\d+$"))
async def cb_page(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await call.answer()
    text, markup = list_view(lang, await db.list_faq(), int((call.data or "").split(":")[-1]))
    await _edit(call, text, markup)


@faq_router.callback_query(F.data.regexp(r"^faq:\d+:\d+$"))
async def cb_item(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    _, raw_id, raw_page = (call.data or "").split(":")
    item = await db.get_faq(int(raw_id))
    if item is None:  # вопрос удалён, пока у пользователя висел старый список
        await call.answer(t(lang, "faq_missing"), show_alert=True)
        text, markup = list_view(lang, await db.list_faq(), int(raw_page))
        await _edit(call, text, markup)
        return
    await call.answer()
    try:  # статистика: какие вопросы открывают чаще всего
        await db.log_event(f"faq.{item['id']}")
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось записать просмотр FAQ")
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_back_inline"), callback_data=f"faq:p:{int(raw_page)}")]])
    await _edit(call, render_card(lang, item), back)
