from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

import data
from texts import LANGS, t


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [t(lang, "btn_clubs"), t(lang, "btn_events")],
        [t(lang, "btn_news"), t(lang, "btn_board")],
        [t(lang, "btn_about"), t(lang, "btn_faq")],
        [t(lang, "btn_feedback"), t(lang, "btn_lang")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
    )


def language_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"lang:{code}")] for code, label in LANGS.items()
        ]
    )


def clubs_inline(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{club['emoji']} {club['name'][lang]}", callback_data=f"club:{i}")]
        for i, club in enumerate(data.CLUBS)
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_quiz"), callback_data="qz:")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def club_back_inline(lang: str, index: int | None = None) -> InlineKeyboardMarkup:
    """Кнопки под карточкой клуба: «Вступить» (если известен номер клуба) и «Назад»."""
    rows = []
    if index is not None:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_join"), callback_data=f"join:{index}")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back_inline"), callback_data="club:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
