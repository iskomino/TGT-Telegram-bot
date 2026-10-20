"""Актуальный контент бота: люди (сədr, müavin, команда TGT), описания клубов, комната и адрес.

Значения по умолчанию лежат в data.py; всё, что меняет админ, хранится в БД и подгружается при старте.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

import data
import db

logger = logging.getLogger(__name__)

# Азербайджан живёт по UTC+4 без перехода на летнее время
BAKU_TZ = timezone(timedelta(hours=4))

NAME_MAX = 40
ROLE_MAX = 60
ROOM_MAX = 20
TEXT_MIN, TEXT_MAX = 10, 700

_CLUB_KEY_RE = re.compile(r"^c\.([a-z]+)\.(chair|deputy)$")
_TEAM_KEY_RE = re.compile(r"^t\.(\d+)$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_people: dict[str, dict[str, str]] = {}   # то, что сохранил админ
_descriptions: dict[str, str] = {}        # slug клуба -> свой текст описания
_info: dict[str, str] = {}                # room / address / about


# ---------- ключи людей ----------

def club_person_key(slug: str, which: str) -> str:
    return f"c.{slug}.{which}"


def team_person_key(slot: int) -> str:
    return f"t.{slot}"


def parse_key(key: str):
    """('club', индекс_клуба, 'chair'|'deputy') / ('team', слот, None) / None, если ключ неверный."""
    match = _CLUB_KEY_RE.match(key or "")
    if match:
        for index, club in enumerate(data.CLUBS):
            if club["slug"] == match.group(1):
                return ("club", index, match.group(2))
        return None
    match = _TEAM_KEY_RE.match(key or "")
    if match and int(match.group(1)) < data.TEAM_SLOTS:
        return ("team", int(match.group(1)), None)
    return None


def fields_for(key: str) -> tuple[str, ...]:
    parsed = parse_key(key)
    if parsed is None:
        return ()
    return data.CLUB_FIELDS if parsed[0] == "club" else data.TEAM_FIELDS


def get_person(key: str) -> dict[str, str]:
    record = dict(data.EMPTY_PERSON)
    record.update(_people.get(key) or data.DEFAULT_PEOPLE.get(key) or {})
    return record


def is_filled(person: dict[str, str]) -> bool:
    return bool(person.get("first_name") or person.get("last_name"))


def _role_key(role: str) -> str:
    """Нормализация для сравнения должностей: без точек и пробелов, I/İ/ı считаются одной буквой."""
    text = (role or "").replace("İ", "i").replace("I", "i").replace("ı", "i")
    return re.sub(r"[\s.]+", "", text).casefold()


_ROLE_LOOKUP = {_role_key(name): (name, translations) for name, translations in data.ROLE_TRANSLATIONS.items()}


def localized_role(role: str, lang: str) -> str:
    """Известные должности показываются на языке пользователя в каноническом виде
    (для az: «TGT İdarə Heyətinin V.M.İ.E. Sədri»), остальные — как ввёл админ."""
    known = _ROLE_LOOKUP.get(_role_key(role))
    if known:
        canonical, translations = known
        return canonical if lang == "az" else translations.get(lang, canonical)
    return role


def full_name(person: dict[str, str]) -> str:
    return " ".join(p for p in (person.get("first_name"), person.get("last_name"), person.get("patronymic")) if p)


async def save_person_field(key: str, field: str, value: str) -> None:
    if field not in fields_for(key):
        raise ValueError(f"Недопустимое поле {field!r} для {key!r}")
    record = get_person(key)
    record[field] = value
    await db.save_person(key, record)
    _people[key] = record


async def clear_person(key: str) -> None:
    if parse_key(key) is None:
        raise ValueError(f"Неверный ключ {key!r}")
    record = dict(data.EMPTY_PERSON)
    await db.save_person(key, record)
    _people[key] = record


# ---------- описания клубов ----------

def get_description(slug: str, lang: str) -> str:
    if slug in _descriptions:
        return _descriptions[slug]
    club = next(c for c in data.CLUBS if c["slug"] == slug)
    return club["desc"].get(lang) or club["desc"]["az"]


async def set_description(slug: str, text: str) -> None:
    await db.kv_set(f"club_desc.{slug}", text)
    _descriptions[slug] = text


async def reset_description(slug: str) -> None:
    await db.kv_delete(f"club_desc.{slug}")
    _descriptions.pop(slug, None)


# ---------- комната, адрес, «О TGT» ----------

def get_room() -> str:
    return _info.get("room", data.DEFAULT_ROOM)


def get_address() -> str:
    return _info.get("address", data.UNIVERSITY_ADDRESS)


def get_about(lang: str) -> str:
    return _info.get("about") or data.TGT_ABOUT.get(lang) or data.TGT_ABOUT["az"]


async def set_info(field: str, value: str) -> None:
    """room / address: пустое значение скрывает строку; about: пустое значение возвращает стандартный текст."""
    if field not in ("room", "address", "about"):
        raise ValueError(f"Неизвестное поле {field!r}")
    if field == "about" and not value:
        await db.kv_delete("info.about")
        _info.pop("about", None)
        return
    await db.kv_set(f"info.{field}", value)
    _info[field] = value


async def load() -> None:
    """Подтягивает сохранённые данные из БД при старте."""
    _people.clear(); _descriptions.clear(); _info.clear()
    for key, record in (await db.load_people()).items():
        if parse_key(key) is not None:
            _people[key] = record
    head = _people.get("t.0")
    if head and head.get("role") in data.LEGACY_HEAD_ROLES:  # обновление со старой версии бота
        head["role"] = data.HEAD_ROLE
        await db.save_person("t.0", head)
    valid_slugs = {c["slug"] for c in data.CLUBS}
    for slug, text in (await db.kv_items("club_desc.")).items():
        if slug in valid_slugs:
            _descriptions[slug] = text
    for field, value in (await db.kv_items("info.")).items():
        if field in ("room", "address", "about"):
            _info[field] = value


# ---------- проверка ввода администратора ----------

def normalize_phone(raw: str) -> str | None:
    """Приводит азербайджанский номер к виду +994 55 766 73 78. Лишний 0 после кода страны убирается."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("994"):
        rest = digits[3:]
        if rest.startswith("0"):
            rest = rest[1:]
    elif digits.startswith("0"):
        rest = digits[1:]
    else:
        rest = digits
    if len(rest) != 9 or rest.startswith("0"):
        return None
    return f"+994 {rest[:2]} {rest[2:5]} {rest[5:7]} {rest[7:9]}"


def validate(field: str, raw: str) -> tuple[str | None, str]:
    """Возвращает (ключ_ошибки | None, нормализованное_значение). Значение «-» означает «очистить»/«по умолчанию»."""
    value = (raw or "").strip()
    if value == "-":
        return None, ""
    if field == "role":
        if not 1 <= len(value) <= ROLE_MAX or "\n" in value:
            return "err_role", ""
        return None, value
    if field in ("first_name", "last_name", "patronymic"):
        if not 1 <= len(value) <= NAME_MAX or "\n" in value:
            return "err_name", ""
        return None, value
    if field == "phone":
        phone = normalize_phone(value)
        return (None, phone) if phone else ("err_phone", "")
    if field == "email":
        if len(value) > 100 or not _EMAIL_RE.match(value):
            return "err_email", ""
        return None, value
    if field == "room":
        if not 1 <= len(value) <= ROOM_MAX or "\n" in value:
            return "err_room", ""
        return None, value
    if field == "address":
        if not 5 <= len(value) <= 200 or "\n" in value:
            return "err_address", ""
        return None, value
    if field in ("desc", "about"):
        if not TEXT_MIN <= len(value) <= TEXT_MAX:
            return "err_text", ""
        return None, value
    return "err_name", ""


# ---------- время (по Баку) ----------

_DT_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})[ T]+(\d{1,2})[:.](\d{2})$")


def parse_event_datetime(raw: str) -> int | None:
    """«25.11.2026 18:00» (время по Баку) -> unix-время; None, если формат или дата неверны."""
    match = _DT_RE.match((raw or "").strip())
    if not match:
        return None
    day, month, year, hour, minute = (int(g) for g in match.groups())
    try:
        return int(datetime(year, month, day, hour, minute, tzinfo=BAKU_TZ).timestamp())
    except ValueError:
        return None


def format_dt(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, BAKU_TZ).strftime("%d.%m.%Y %H:%M")


def short_dt(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, BAKU_TZ).strftime("%d.%m %H:%M")


# ---------- проверка ввода: заявки, события, обращения ----------

def validate_input(kind: str, raw: str) -> tuple[str | None, object]:
    """Возвращает (ключ_ошибки | None, значение). «-» для необязательных полей даёт пустое значение."""
    value = (raw or "").strip()
    single_line = "\n" not in value
    if kind == "app_name":
        return (None, value) if 2 <= len(value) <= 60 and single_line else ("err_join_name", "")
    if kind == "app_faculty":
        return (None, value) if 2 <= len(value) <= 80 and single_line else ("err_join_faculty", "")
    if kind == "app_phone":
        if value == "-":
            return None, ""
        phone = normalize_phone(value)
        return (None, phone) if phone else ("err_join_phone", "")
    if kind == "fb_text":
        return (None, value) if 10 <= len(value) <= 1000 else ("err_fb_text", "")
    if kind == "reply_text":
        return (None, value) if 2 <= len(value) <= 1000 else ("err_reply", "")
    if kind == "event_title":
        return (None, value) if 3 <= len(value) <= 80 and single_line else ("err_event_title", "")
    if kind == "event_place":
        if value == "-":
            return None, ""
        return (None, value) if 2 <= len(value) <= 100 and single_line else ("err_event_place", "")
    if kind == "event_desc":
        if value == "-":
            return None, ""
        return (None, value) if 10 <= len(value) <= 700 else ("err_event_desc", "")
    if kind == "event_capacity":
        if value == "-":
            return None, None
        if value.isdigit() and 1 <= int(value) <= 10000:
            return None, int(value)
        return "err_event_capacity", None
    return "err_event_title", ""


def format_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, BAKU_TZ).strftime("%d.%m.%Y")


def short_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, BAKU_TZ).strftime("%d.%m")


# ---------- проверка ввода: новости ----------

def validate_link(raw: str) -> str | None:
    """Адрес http(s) без пробелов, не длиннее 300 символов; иначе None."""
    from urllib.parse import urlparse

    value = (raw or "").strip()
    if not value or len(value) > 300 or any(ch.isspace() for ch in value):
        return None
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc else None


def validate_news(kind: str, raw: str) -> tuple[str | None, str]:
    """kind: news_title | news_body | news_link. «-» для ссылки означает «без ссылки»."""
    value = (raw or "").strip()
    if kind == "news_title":
        return (None, value) if 3 <= len(value) <= 80 and "\n" not in value else ("err_nw_title", "")
    if kind == "news_body":
        return (None, value) if 10 <= len(value) <= 700 else ("err_nw_body", "")
    if kind == "news_link":
        if value == "-":
            return None, ""
        link = validate_link(value)
        return (None, link) if link else ("err_nw_link", "")
    return "err_nw_title", ""


# ---------- FAQ ----------

FAQ_Q_MIN, FAQ_Q_MAX = 5, 200
FAQ_A_MIN, FAQ_A_MAX = 10, 1500


def faq_text(item: dict, lang: str) -> tuple[str, str]:
    """(вопрос, ответ) на языке пользователя; если перевод неполный (нет вопроса или ответа), показывается азербайджанский."""
    if lang != "az" and item.get(f"q_{lang}") and item.get(f"a_{lang}"):
        return item[f"q_{lang}"], item[f"a_{lang}"]
    return item["q_az"], item["a_az"]


def has_translation(item: dict, lang: str) -> bool:
    return bool(item.get(f"q_{lang}") and item.get(f"a_{lang}"))


def validate_faq(field: str, raw: str) -> tuple[str | None, str]:
    """field: q_az | a_az | q_ru | a_ru | q_en | a_en. «-» очищает перевод (для az недопустимо)."""
    value = (raw or "").strip()
    is_question = field.startswith("q_")
    if value == "-" and not field.endswith("_az"):
        return None, ""
    if is_question:
        ok = FAQ_Q_MIN <= len(value) <= FAQ_Q_MAX and "\n" not in value
        return (None, value) if ok else ("err_fq_q", "")
    return (None, value) if FAQ_A_MIN <= len(value) <= FAQ_A_MAX else ("err_fq_a", "")


async def seed_faq() -> int:
    """При самом первом запуске записывает исходные вопросы. Если админ потом всё удалил, повторно не добавляет."""
    if await db.kv_get("faq_seeded") is not None:
        return 0
    added = 0
    if await db.faq_count() == 0:
        for item in data.DEFAULT_FAQ:
            await db.add_faq(
                {
                    "q_az": item["q"]["az"], "a_az": item["a"]["az"],
                    "q_ru": item["q"]["ru"], "a_ru": item["a"]["ru"],
                    "q_en": item["q"]["en"], "a_en": item["a"]["en"],
                }
            )
            added += 1
    await db.kv_set("faq_seeded", "1")
    return added

