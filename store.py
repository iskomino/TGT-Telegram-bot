"""Язык пользователей в памяти (при запуске подгружается из БД)."""
USER_LANG: dict[int, str] = {}
DEFAULT_LANG = "az"


def get_lang(uid: int) -> str:
    return USER_LANG.get(uid, DEFAULT_LANG)
