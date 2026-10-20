"""Новости TGT для студентов: список, карточка (с фото и ссылкой), подписка на уведомления о новых новостях."""
import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import content
import db
from flows import is_btn
from store import get_lang
from texts import t

logger = logging.getLogger(__name__)

news_router = Router(name="news")
news_router.message.filter(F.chat.type == "private")

LIST_SIZE = 10


def render_news(item: dict, header: str = "") -> str:
    return (
        f"{header}📰 <b>{html.escape(item['title'])}</b>\n"
        f"📅 {content.format_date(item['created'])}\n\n{html.escape(item['body'])}"
    )


def card_markup(lang: str, item: dict, *, back: bool, unsubscribe: bool = False) -> InlineKeyboardMarkup | None:
    rows = []
    if item.get("link"):
        rows.append([InlineKeyboardButton(text=t(lang, "btn_news_link"), url=item["link"])])
    if unsubscribe:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_news_sub_off"), callback_data="nsub:off")])
    if back:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_back_inline"), callback_data="news:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def list_markup(lang: str, items: list[dict], subscribed: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📰 {content.short_date(i['created'])} · {i['title']}"[:60], callback_data=f"news:{i['id']}")]
        for i in items
    ]
    toggle = "btn_news_sub_off" if subscribed else "btn_news_sub_on"
    rows.append([InlineKeyboardButton(text=t(lang, toggle), callback_data="nsub:toggle")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_card(bot: Bot, chat_id: int, lang: str, item: dict, *, header: str = "", markup: InlineKeyboardMarkup | None = None) -> None:
    """Отправляет новость: с фото (подпись), а если Telegram отклонил фото, то обычным текстом."""
    text = render_news(item, header)
    if item.get("photo_id"):
        try:
            await bot.send_photo(chat_id, item["photo_id"], caption=text, reply_markup=markup)
            return
        except TelegramBadRequest:
            logger.warning("Фото новости %s недоступно, отправляется текст", item.get("id"))
    try:
        await bot.send_message(chat_id, text, reply_markup=markup)
    except TelegramBadRequest:
        if markup is None:
            raise
        # Telegram отклонил кнопки (например, странная ссылка): текст новости важнее, отправляем без кнопок
        logger.warning("Кнопки новости %s отклонены Telegram, отправляется только текст", item.get("id"))
        await bot.send_message(chat_id, text)


async def broadcast_news(bot: Bot, item: dict) -> dict[str, int]:
    """Рассылает новость подписчикам (каждому на его языке) с кнопкой «Отписаться»."""
    stats = {"sent": 0, "blocked": 0, "failed": 0}
    for uid in await db.news_subscribers():
        lang = get_lang(uid)
        kwargs = dict(header=t(lang, "news_alert_head"), markup=card_markup(lang, item, back=False, unsubscribe=True))
        try:
            try:
                await send_card(bot, uid, lang, item, **kwargs)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                await send_card(bot, uid, lang, item, **kwargs)
            stats["sent"] += 1
        except TelegramForbiddenError:
            stats["blocked"] += 1
            await db.mark_blocked(uid)
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить новость пользователю %s", uid)
            stats["failed"] += 1
        await asyncio.sleep(0.05)  # ~20 сообщений/с, ниже лимита Telegram
    return stats


async def _show_list(lang: str, uid: int) -> tuple[str, InlineKeyboardMarkup]:
    items = await db.list_news(LIST_SIZE)
    subscribed = await db.is_news_subscribed(uid)
    return t(lang, "news_title" if items else "news_empty"), list_markup(lang, items, subscribed)


@news_router.message(is_btn("btn_news"))
async def news_menu(message: Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return
    lang = get_lang(message.from_user.id)
    text, markup = await _show_list(lang, message.from_user.id)
    await message.answer(text, reply_markup=markup)


@news_router.callback_query(F.data == "news:list")
async def cb_list(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    await call.answer()
    text, markup = await _show_list(lang, call.from_user.id)
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


@news_router.callback_query(F.data.regexp(r"^news:\d+$"))
async def cb_item(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await db.get_news(int((call.data or "").split(":")[-1]))
    if item is None:
        await call.answer(t(lang, "news_missing"), show_alert=True)
        return
    await call.answer()
    if item["photo_id"]:  # сообщение с фото нельзя «превратить» в текст: отправляем отдельным сообщением, список остаётся выше
        await send_card(call.bot, call.from_user.id, lang, item, markup=card_markup(lang, item, back=False))
    elif isinstance(call.message, Message):
        try:
            await call.message.edit_text(render_news(item), reply_markup=card_markup(lang, item, back=True))
        except TelegramBadRequest:
            pass


@news_router.callback_query(F.data.regexp(r"^nsub:(toggle|off)$"))
async def cb_subscribe(call: CallbackQuery):
    uid = call.from_user.id
    lang = get_lang(uid)
    action = (call.data or "").split(":")[-1]
    if action == "off":  # кнопка под самим уведомлением: убираем только её, ссылка остаётся
        await db.set_news_subscription(uid, False)
        await call.answer(t(lang, "news_sub_disabled"))
        if isinstance(call.message, Message):
            old = call.message.reply_markup.inline_keyboard if call.message.reply_markup else []
            rows = [[b for b in row if b.callback_data != "nsub:off"] for row in old]
            rows = [row for row in rows if row]
            try:
                await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)
            except TelegramBadRequest:
                pass
        return
    enabled = not await db.is_news_subscribed(uid)
    await db.set_news_subscription(uid, enabled)
    await call.answer(t(lang, "news_sub_enabled" if enabled else "news_sub_disabled"))
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(reply_markup=list_markup(lang, await db.list_news(LIST_SIZE), enabled))
        except TelegramBadRequest:
            pass
