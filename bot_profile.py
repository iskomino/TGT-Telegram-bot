"""Оформление бота в Telegram: описание, краткое описание (только на азербайджанском) и команды.

Описание и «About» одинаковы для всех пользователей; отдельные версии для русского и английского
языков Telegram удаляются (пустая строка). Команды в меню бота — на языке пользователя.
Лимиты Telegram: описание до 512 символов, краткое до 120, описание команды до 256.
"""
import logging

from aiogram import Bot
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)

DESCRIPTION = {
    "az": """🎓 ATU Tələbə Gənclər Təşkilatı (TGT) üçün məlumat botu!

🎭 Klublar, klub testi və qoşulmaq üçün müraciət
📅 Tədbirlər və qeydiyyat
📰 TGT xəbərləri
❓ Tez-tez verilən suallar
🏛 TGT İdarə Heyəti
✉️ Təklif və şikayətlər (istəsəniz anonim)
ℹ️ TGT haqqında: rəhbər, otaq və ünvan
🌐 Azərbaycan, rus və ingilis dilləri

Başlamaq üçün /start düyməsini basın!""",
}

SHORT_DESCRIPTION = {
    "az": "ATU TGT: klublar, sədrlər və əlaqə məlumatları 🎓",
}

COMMANDS = {
    "az": [("start", "Başla"), ("menu", "Əsas menyu"), ("help", "Kömək"), ("cancel", "Ləğv et")],
    "ru": [("start", "Начать"), ("menu", "Главное меню"), ("help", "Помощь"), ("cancel", "Отмена")],
    "en": [("start", "Start"), ("menu", "Main menu"), ("help", "Help"), ("cancel", "Cancel")],
}

REMOVE_DEDICATED_FOR = ("ru", "en")


async def setup_profile(bot: Bot) -> None:
    """Применяет оформление. Каждый вызов независим: сбой одного не мешает остальным и запуску бота."""
    description, short = DESCRIPTION["az"], SHORT_DESCRIPTION["az"]
    calls: list[tuple[str, object]] = []

    for code in (None, "az"):
        label = code or "по умолчанию"
        calls.append((f"описание ({label})", lambda c=code: bot.set_my_description(description=description, language_code=c)))
        calls.append((f"краткое описание ({label})", lambda c=code: bot.set_my_short_description(short_description=short, language_code=c)))

    for code in REMOVE_DEDICATED_FOR:
        calls.append((f"описание ({code}): удаление", lambda c=code: bot.set_my_description(description="", language_code=c)))
        calls.append((f"краткое описание ({code}): удаление", lambda c=code: bot.set_my_short_description(short_description="", language_code=c)))

    for code in (None, "az", "ru", "en"):
        texts_lang = code or "az"
        label = code or "по умолчанию"
        commands = [BotCommand(command=c, description=d) for c, d in COMMANDS[texts_lang]]
        calls.append((f"команды ({label})", lambda c=code, cmds=commands: bot.set_my_commands(cmds, language_code=c)))

    for what, call in calls:
        try:
            await call()
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось обновить профиль бота: %s", what)
