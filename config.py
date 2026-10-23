import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Создайте файл .env по образцу .env.example")

ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
]

# Подпись разработчика (показывается в «О TGT» и в справке). Пустое имя отключает подпись.
DEVELOPER_NAME: str = os.getenv("DEVELOPER_NAME", "Ismail Mikailov").strip()
# Необязательный контакт: @username в Telegram (станет ссылкой) или любой короткий текст
DEVELOPER_CONTACT: str = os.getenv("DEVELOPER_CONTACT", "").strip()

DB_PATH: str = os.getenv("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")
