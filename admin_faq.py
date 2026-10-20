"""Админ-панель, часть 4: FAQ (добавление, редактирование с переводами, порядок, удаление).

Роутер подключается ДО основного админ-роутера (см. main.py).
"""
import html
import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import content
import db
from admin import _edit, _kb
from admin_texts import at
from config import ADMIN_IDS
from faq import render_card
from flows import PLAIN_TEXT, stray_input
from store import get_lang

logger = logging.getLogger(__name__)

admin_faq_router = Router(name="admin_faq")
admin_faq_router.message.filter(F.chat.type == "private", F.from_user.id.in_(ADMIN_IDS))
admin_faq_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

FIELDS = ("q_az", "a_az", "q_ru", "a_ru", "q_en", "a_en")
LIST_LIMIT = 40


class FaqCreate(StatesGroup):
    question = State()
    answer = State()


class FaqEdit(StatesGroup):
    value = State()


def _int(raw: str) -> int | None:
    return int(raw) if raw.isdigit() and len(raw) <= 12 else None


def _limits(field: str) -> dict:
    return {"min": content.FAQ_Q_MIN, "max": content.FAQ_Q_MAX} if field.startswith("q_") else {"min": content.FAQ_A_MIN, "max": content.FAQ_A_MAX}


def _field_label(lang: str, field: str) -> str:
    return f"{at(lang, 'f_fq_' + field[0])} ({field[2:]})"


async def _list_view(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    items = await db.list_faq()
    rows = [[(at(lang, "btn_new_faq"), "adm:fqnew")]]
    rows += [[(f"❓ {i['q_az']}"[:60], f"adm:fqv:{i['id']}")] for i in items[:LIST_LIMIT]]
    rows.append([(at(lang, "btn_home"), "adm:home")])
    return at(lang, "fq_admin", count=len(items)), _kb(rows)


async def _item_view(lang: str, item: dict) -> tuple[str, InlineKeyboardMarkup]:
    items = await db.list_faq()
    position = next((n for n, i in enumerate(items, 1) if i["id"] == item["id"]), 0)
    mark = lambda code: at(lang, "fq_tr_yes") if content.has_translation(item, code) else at(lang, "fq_tr_no")  # noqa: E731
    text = at(
        lang,
        "fq_view",
        q=html.escape(item["q_az"]),
        a=html.escape(item["a_az"]),
        pos=position,
        total=len(items),
        ru=mark("ru"),
        en=mark("en"),
    )
    fid = item["id"]
    rows = []
    for code in ("az", "ru", "en"):
        rows.append([(f"✏️ {_field_label(lang, f'q_{code}')}", f"adm:fqf:{fid}:q_{code}"), (f"✏️ {_field_label(lang, f'a_{code}')}", f"adm:fqf:{fid}:a_{code}")])
    rows.append([(at(lang, "btn_fq_up"), f"adm:fqu:{fid}"), (at(lang, "btn_fq_down"), f"adm:fqd:{fid}")])
    rows.append([(at(lang, "btn_fq_preview"), f"adm:fqp:{fid}")])
    rows.append([(at(lang, "btn_fq_delete"), f"adm:fqx:{fid}")])
    rows.append([(at(lang, "btn_back"), "adm:fq")])
    return text, _kb(rows)


async def _get(raw: str) -> dict | None:
    faq_id = _int(raw)
    return await db.get_faq(faq_id) if faq_id is not None else None


async def _gone(call: CallbackQuery, lang: str) -> None:
    await call.answer(at(lang, "fq_gone"), show_alert=True)
    text, markup = await _list_view(lang)
    await _edit(call, text, markup)


@admin_faq_router.callback_query(F.data == "adm:fq")
async def cb_list(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    text, markup = await _list_view(get_lang(call.from_user.id))
    await _edit(call, text, markup)


@admin_faq_router.callback_query(F.data.startswith("adm:fqv:"))
async def cb_view(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await state.clear()
    await call.answer()
    text, markup = await _item_view(lang, item)
    await _edit(call, text, markup)


@admin_faq_router.callback_query(F.data.startswith("adm:fqp:"))
async def cb_preview(call: CallbackQuery):
    """Присылает администратору карточку так, как её видят пользователи на его языке."""
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await call.answer()
    await call.bot.send_message(call.from_user.id, render_card(lang, item))


# ---------- создание ----------

@admin_faq_router.callback_query(F.data == "adm:fqnew")
async def cb_new(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    await state.clear()
    await state.set_state(FaqCreate.question)
    await call.answer()
    await _edit(call, at(lang, "fq_ask_q", **_limits("q_az")), _kb([[(at(lang, "btn_cancel"), "adm:fq")]]))


@admin_faq_router.message(FaqCreate.question, *PLAIN_TEXT)
async def create_question(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_faq("q_az", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error, **_limits('q_az'))}\n{at(lang, 'retry')}")
        return
    await state.update_data(question=value)
    await state.set_state(FaqCreate.answer)
    await message.answer(at(lang, "fq_ask_a", **_limits("a_az")))


@admin_faq_router.message(FaqCreate.answer, *PLAIN_TEXT)
async def create_answer(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    error, value = content.validate_faq("a_az", message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error, **_limits('a_az'))}\n{at(lang, 'retry')}")
        return
    question = (await state.get_data()).get("question")
    await state.clear()
    if not question:
        return
    faq_id = await db.add_faq({"q_az": question, "a_az": value})
    text, markup = await _item_view(lang, await db.get_faq(faq_id))
    await message.answer(at(lang, "fq_saved_new") + "\n\n" + text, reply_markup=markup)


@admin_faq_router.message(StateFilter(FaqCreate.question, FaqCreate.answer), stray_input)
async def create_wrong(message: Message):
    await message.answer(f"❗️ {at(get_lang(message.from_user.id), 'retry')}")


# ---------- редактирование (текст и переводы) ----------

@admin_faq_router.callback_query(F.data.startswith("adm:fqf:"))
async def cb_edit(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    parts = (call.data or "").split(":")
    faq_id = _int(parts[2]) if len(parts) == 4 else None
    field = parts[3] if len(parts) == 4 else ""
    if faq_id is None or field not in FIELDS:
        await call.answer()
        return
    if await db.get_faq(faq_id) is None:
        await _gone(call, lang)
        return
    hint = at(lang, "fq_hint_az" if field.endswith("_az") else "fq_hint_tr")
    await state.clear()
    await state.set_state(FaqEdit.value)
    await state.update_data(faq_id=faq_id, field=field)
    await call.answer()
    await _edit(
        call,
        at(lang, "fq_edit_ask", field=_field_label(lang, field), hint=hint),
        _kb([[(at(lang, "btn_cancel"), f"adm:fqv:{faq_id}")]]),
    )


@admin_faq_router.message(FaqEdit.value, *PLAIN_TEXT)
async def got_edit(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    stored = await state.get_data()
    faq_id, field = stored.get("faq_id"), stored.get("field")
    if not isinstance(faq_id, int) or field not in FIELDS:
        await state.clear()
        return
    error, value = content.validate_faq(field, message.text or "")
    if error:
        await message.answer(f"❗️ {at(lang, error, **_limits(field))}\n{at(lang, 'retry')}")
        return
    await db.update_faq(faq_id, field, value)
    await state.clear()
    item = await db.get_faq(faq_id)
    if item is None:
        await message.answer(at(lang, "fq_gone"))
        return
    text, markup = await _item_view(lang, item)
    await message.answer(at(lang, "fq_saved") + "\n\n" + text, reply_markup=markup)


@admin_faq_router.message(StateFilter(FaqEdit.value), stray_input)
async def edit_wrong(message: Message):
    await message.answer(f"❗️ {at(get_lang(message.from_user.id), 'retry')}")


# ---------- порядок ----------

@admin_faq_router.callback_query(F.data.regexp(r"^adm:fq[ud]:\d+$"))
async def cb_move(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    action, raw = (call.data or "").split(":")[1:]
    item = await _get(raw)
    if item is None:
        await _gone(call, lang)
        return
    moved = await db.move_faq(item["id"], -1 if action == "fqu" else 1)
    await call.answer(at(lang, "fq_moved" if moved else "fq_cant_move"))
    if moved:
        text, markup = await _item_view(lang, await db.get_faq(item["id"]))
        await _edit(call, text, markup)


# ---------- удаление ----------

@admin_faq_router.callback_query(F.data.startswith("adm:fqx:"))
async def cb_delete_ask(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await call.answer()
    await _edit(
        call,
        at(lang, "fq_delete_confirm", q=html.escape(item["q_az"])),
        _kb([[(at(lang, "btn_yes_send"), f"adm:fqxy:{item['id']}"), (at(lang, "btn_cancel"), f"adm:fqv:{item['id']}")]]),
    )


@admin_faq_router.callback_query(F.data.startswith("adm:fqxy:"))
async def cb_delete_do(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    item = await _get((call.data or "").split(":")[-1])
    if item is None:
        await _gone(call, lang)
        return
    await db.delete_faq(item["id"])
    await call.answer(at(lang, "fq_deleted"))
    text, markup = await _list_view(lang)
    await _edit(call, text, markup)
