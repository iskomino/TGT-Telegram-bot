"""Админ-панель, часть 3: новости TGT (создание с фото и ссылкой, редактирование, оповещение подписчиков, удаление).

Роутер подключается ДО основного админ-роутера (см. main.py).
"""
import asyncio
import html
import logging
import time

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import content
import db
from admin import _edit, _kb
from admin_texts import at
from config import ADMIN_IDS
from flows import PLAIN_TEXT, stray_input
from news import broadcast_news, send_card
from store import get_lang

logger = logging.getLogger(__name__)

admin_news_router = Router(name="admin_news")
admin_news_router.message.filter(F.chat.type == "private", F.from_user.id.in_(ADMIN_IDS))
admin_news_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

_tasks: set[asyncio.Task] = set()
EDIT_FIELDS = {"title": "title", "body": "body", "photo": "photo_id", "link": "link"}


class NewsCreate(StatesGroup):
    title = State()
    body = State()
    photo = State()
    link = State()
    confirm = State()


class NewsEdit(StatesGroup):
    value = State()


def _int(raw: str) -> int | None:
    return int(raw) if raw.isdigit() and len(raw) <= 12 else None


def _yes_no(lang: str, flag) -> str:
    return at(lang, "nw_yes" if flag else "nw_no")


async def _list_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    items = await db.list_news(20)
    rows = [[(at(lang, "btn_new_news"), "adm:nwnew")]]
    rows += [[(f"📰 {content.short_date(i['created'])} · {i['title']}"[:60], f"adm:nwv:{i['id']}")] for i in items]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    return at(lang, "news_admin", subs=len(await db.news_subscribers())), _kb(rows)


def _item_view(lang: str, item: dict) -> tuple[str, InlineKeyboardMarkup]:
    text = at(
        lang,
        "nw_view",
        title=html.escape(item["title"]),
        date=content.format_date(item["created"]),
        notified=_yes_no(lang, item["notified"]),
        photo=_yes_no(lang, item["photo_id"]),
        link=_yes_no(lang, item["link"]),
        body=html.escape(item["body"]),
    )
    nid = item["id"]
    markup = _kb(
        [
            [(at(lang, "btn_nw_preview"), f"adm:nwpv:{nid}")],
            [(at(lang, "btn_nwf_title"), f"adm:nwf:{nid}:title"), (at(lang, "btn_nwf_body"), f"adm:nwf:{nid}:body")],
            [(at(lang, "btn_nwf_photo"), f"adm:nwf:{nid}:photo"), (at(lang, "btn_nwf_link"), f"adm:nwf:{nid}:link")],
            [(at(lang, "btn_nw_notify"), f"adm:nwn:{nid}")],
            [(at(lang, "btn_nw_delete"), f"adm:nwd:{nid}")],
            [(at(lang, "btn_back"), "adm:nw")],
        ]
    )
    return text, markup


async def _gone(call: CallbackQuery, lang: str) -> None:
    await call.answer(at(lang, "nw_gone"), show_alert=True)
    text, markup = await _list_view(lang)
    await _edit(call, text, markup)


async def _get(raw: str) -> dict | None:
    news_id = _int(raw)
    return await db.get_news(news_id) if news_id is not None else None


@admin_news_router.callback_query(F.data == "adm:nw")
async def cb_list(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = await _list_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_news_router.callback_query(F.data.startswith("adm:nwv:"))
async def cb_view(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await state.clear()
    await call.answer()
    text, markup = _item_view(lang, item)
    await _edit(call, text, markup)


@admin_news_router.callback_query(F.data.startswith("adm:nwpv:"))
async def cb_preview(call: CallbackQuery, bot: Bot):
    """Присылает администратору новость в том виде, в каком её видят пользователи (с фото и кнопкой-ссылкой)."""
    from news import card_markup

    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await call.answer()
    await send_card(bot, call.from_user.id, lang, item, markup=card_markup(lang, item, back=False))


# ---------- создание ----------

@admin_news_router.callback_query(F.data == "adm:nwnew")
async def cb_new(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    await state.clear()
    await state.set_state(NewsCreate.title)
    await call.answer()
    await _edit(call, at(lang, "nw_ask_title"), _kb([[(at(lang, "btn_cancel"), "adm:nw")]]))


@admin_news_router.message(NewsCreate.title, *PLAIN_TEXT)
async def create_title(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_news("news_title", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(title=value)
    await state.set_state(NewsCreate.body)
    await message.answer(at(lang, "nw_ask_body"))


@admin_news_router.message(NewsCreate.body, *PLAIN_TEXT)
async def create_body(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_news("news_body", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(body=value)
    await state.set_state(NewsCreate.photo)
    await message.answer(at(lang, "nw_ask_photo"))


async def _ask_link(message: Message, state: FSMContext, photo_id: str) -> None:
    await state.update_data(photo=photo_id)
    await state.set_state(NewsCreate.link)
    await message.answer(at(get_lang(message.from_user.id), "nw_ask_link"))


@admin_news_router.message(NewsCreate.photo, F.photo)
async def create_photo(message: Message, state: FSMContext):
    await _ask_link(message, state, message.photo[-1].file_id)


@admin_news_router.message(NewsCreate.photo, *PLAIN_TEXT)
async def create_photo_skip(message: Message, state: FSMContext):
    if (message.text or "").strip() == "-":
        await _ask_link(message, state, "")
        return
    lang = get_lang(message.from_user.id)
    await message.answer(f"❗️ {at(lang, 'err_nw_photo')}")


@admin_news_router.message(StateFilter(NewsCreate.photo), stray_input)
async def create_photo_wrong(message: Message):
    await message.answer(f"❗️ {at(get_lang(message.from_user.id), 'err_nw_photo')}")


@admin_news_router.message(NewsCreate.link, *PLAIN_TEXT)
async def create_link(message: Message, state: FSMContext, bot: Bot):
    from news import card_markup

    lang = get_lang(message.from_user.id)
    error, value = content.validate_news("news_link", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
        return
    await state.update_data(link=value)
    await state.set_state(NewsCreate.confirm)
    stored = await state.get_data()
    draft = {"id": 0, "title": stored["title"], "body": stored["body"], "photo_id": stored.get("photo", ""), "link": value, "created": int(time.time())}
    await send_card(bot, message.from_user.id, lang, draft, markup=card_markup(lang, draft, back=False))
    await message.answer(
        at(lang, "nw_preview"),
        reply_markup=_kb(
            [
                [(at(lang, "btn_publish"), "adm:nwp:0")],
                [(at(lang, "btn_publish_notify"), "adm:nwp:1")],
                [(at(lang, "btn_cancel"), "adm:nw")],
            ]
        ),
    )


@admin_news_router.callback_query(F.data.regexp(r"^adm:nwp:[01]$"), StateFilter(NewsCreate.confirm))
async def cb_publish(call: CallbackQuery, state: FSMContext, bot: Bot):
    lang = get_lang(call.from_user.id)
    notify = (call.data or "").endswith(":1")
    stored = await state.get_data()
    await state.clear()
    await call.answer()
    if not stored.get("title") or not stored.get("body"):
        return
    news_id = await db.add_news(stored["title"], stored["body"], stored.get("photo", ""), stored.get("link", ""))
    item = await db.get_news(news_id)
    notice = at(lang, "nw_published")
    if notify:
        await db.set_news_notified(news_id)
        count = len(await db.news_subscribers())
        notice += " " + at(lang, "nw_publish_notified", count=count)
        _start_broadcast(bot, call.from_user.id, item)
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass
    text, markup = _item_view(lang, await db.get_news(news_id))
    await bot.send_message(call.from_user.id, notice + "\n\n" + text, reply_markup=markup)


def _start_broadcast(bot: Bot, admin_id: int, item: dict) -> None:
    task = asyncio.create_task(_notify(bot, admin_id, item))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _notify(bot: Bot, admin_id: int, item: dict) -> None:
    stats = await broadcast_news(bot, item)
    try:
        await bot.send_message(admin_id, at(get_lang(admin_id), "nw_notify_report", **stats))
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось отправить отчёт о рассылке новости администратору %s", admin_id)


# ---------- редактирование ----------

@admin_news_router.callback_query(F.data.startswith("adm:nwf:"))
async def cb_edit(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    parts = (call.data or "").split(":")
    news_id = _int(parts[2]) if len(parts) == 4 else None
    field = parts[3] if len(parts) == 4 else ""
    if news_id is None or field not in EDIT_FIELDS:
        await call.answer()
        return
    if await db.get_news(news_id) is None:
        await _gone(call, lang)
        return
    hint = {"link": at(lang, "nw_hint_link"), "photo": at(lang, "nw_hint_photo")}.get(field, at(lang, "nw_hint_required"))
    await state.clear()
    await state.set_state(NewsEdit.value)
    await state.update_data(news_id=news_id, field=field)
    await call.answer()
    await _edit(
        call,
        at(lang, "nw_edit_ask", field=at(lang, f"f_nw_{field}"), hint=hint),
        _kb([[(at(lang, "btn_cancel"), f"adm:nwv:{news_id}")]]),
    )


async def _finish_edit(message: Message, state: FSMContext, news_id: int, db_field: str, value: str) -> None:
    lang = get_lang(message.from_user.id)
    await db.update_news(news_id, db_field, value)
    await state.clear()
    item = await db.get_news(news_id)
    if item is None:
        await message.answer(at(lang, "nw_gone"))
        return
    text, markup = _item_view(lang, item)
    await message.answer(at(lang, "nw_saved") + "\n\n" + text, reply_markup=markup)


@admin_news_router.message(NewsEdit.value, F.photo)
async def edit_photo(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    stored = await state.get_data()
    if stored.get("field") != "photo" or not isinstance(stored.get("news_id"), int):
        await message.answer(f"❗️ {at(lang, 'retry')}")
        return
    await _finish_edit(message, state, stored["news_id"], "photo_id", message.photo[-1].file_id)


@admin_news_router.message(NewsEdit.value, *PLAIN_TEXT)
async def edit_text(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    stored = await state.get_data()
    news_id, field = stored.get("news_id"), stored.get("field")
    if not isinstance(news_id, int) or field not in EDIT_FIELDS:
        await state.clear()
        return
    text = (message.text or "").strip()
    if field == "photo":
        if text != "-":
            await message.answer(f"❗️ {at(lang, 'err_nw_photo')}")
            return
        value = ""
    elif field == "link":
        error, value = content.validate_news("news_link", text)
        if error:
            await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
            return
    else:
        error, value = content.validate_news(f"news_{field}", text)
        if error:
            await message.answer(f"❗️ {at(lang, error)}\n{at(lang, 'retry')}")
            return
    await _finish_edit(message, state, news_id, EDIT_FIELDS[field], value)


@admin_news_router.message(StateFilter(NewsEdit.value), stray_input)
async def edit_wrong(message: Message):
    await message.answer(f"❗️ {at(get_lang(message.from_user.id), 'retry')}")


# ---------- оповещение подписчиков ----------

@admin_news_router.callback_query(F.data.startswith("adm:nwn:"))
async def cb_notify_ask(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    if item["notified"]:
        await call.answer(at(lang, "nw_notify_already"), show_alert=True)
        return
    count = len(await db.news_subscribers())
    if not count:
        await call.answer(at(lang, "nw_notify_none"), show_alert=True)
        return
    await call.answer()
    await _edit(
        call,
        at(lang, "nw_notify_confirm", title=html.escape(item["title"]), count=count),
        _kb([[(at(lang, "btn_yes_send"), f"adm:nwny:{item['id']}"), (at(lang, "btn_cancel"), f"adm:nwv:{item['id']}")]]),
    )


@admin_news_router.callback_query(F.data.startswith("adm:nwny:"))
async def cb_notify_do(call: CallbackQuery, bot: Bot):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    if item["notified"]:
        await call.answer(at(lang, "nw_notify_already"), show_alert=True)
        return
    await db.set_news_notified(item["id"])  # помечаем до отправки: повторное нажатие не создаст дубль
    await call.answer()
    await _edit(call, at(lang, "nw_notify_started"), _kb([[(at(lang, "btn_back"), f"adm:nwv:{item['id']}")]]))
    _start_broadcast(bot, call.from_user.id, item)


# ---------- удаление ----------

@admin_news_router.callback_query(F.data.startswith("adm:nwd:"))
async def cb_delete_ask(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await call.answer()
    await _edit(
        call,
        at(lang, "nw_delete_confirm", title=html.escape(item["title"])),
        _kb([[(at(lang, "btn_yes_send"), f"adm:nwdy:{item['id']}"), (at(lang, "btn_cancel"), f"adm:nwv:{item['id']}")]]),
    )


@admin_news_router.callback_query(F.data.startswith("adm:nwdy:"))
async def cb_delete_do(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await db.delete_news(item["id"])
    await call.answer(at(lang, "nw_deleted"))
    text, markup = await _list_view(lang)
    await _edit(call, text, markup)
