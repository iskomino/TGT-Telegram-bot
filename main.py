import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import content
import db
from admin import admin_router
from admin_extra import admin_extra_router
from admin_faq import admin_faq_router
from admin_news import admin_news_router
from bot_profile import setup_profile
from config import ADMIN_IDS, BOT_TOKEN, DB_PATH
from events import events_router
from faq import faq_router
from feedback import feedback_router
from flows import flow_router
from handlers import router
from join import join_router
from middleware import StatsMiddleware, ThrottlingMiddleware
from news import news_router
from quiz import quiz_router
from reminders import reminders_loop
from store import USER_LANG


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    db.init(DB_PATH)
    USER_LANG.update(await db.load_langs())
    await content.load()
    await content.seed_faq()  # при первом запуске записывает исходные вопросы FAQ

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    throttle = ThrottlingMiddleware(limit=10, window=10.0, exempt=ADMIN_IDS)
    dp.message.outer_middleware(throttle)
    dp.callback_query.outer_middleware(throttle)
    dp.message.outer_middleware(StatsMiddleware())
    # Порядок важен: админские роутеры (часть 2 — раньше части 1, в которой есть «обработчик устаревших кнопок»),
    # затем диалоги пользователя и, последним, основной роутер с обработчиком «непонятных» сообщений.
    for included in (
        admin_extra_router, admin_news_router, admin_faq_router, admin_router,
        flow_router, join_router, events_router, feedback_router, quiz_router, news_router, faq_router, router,
    ):
        dp.include_router(included)

    await setup_profile(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    reminders_task = asyncio.create_task(reminders_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        reminders_task.cancel()
        await bot.session.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
