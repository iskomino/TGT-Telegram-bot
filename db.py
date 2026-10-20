"""SQLite-хранилище: пользователи (только ID и язык), статистика, люди (сədr и пр.), настройки.

Персональные данные студентов бот не собирает. Телефоны и имена руководителей клубов вносит админ.
"""
import asyncio
import sqlite3
import threading
import time

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    lang TEXT,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    blocked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS people (
    key TEXT PRIMARY KEY,
    role TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    patronymic TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    faculty TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    created INTEGER NOT NULL,
    decided INTEGER
);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);
CREATE TABLE IF NOT EXISTS tgt_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    place TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    starts_at INTEGER NOT NULL,
    capacity INTEGER,
    notified INTEGER NOT NULL DEFAULT 0,
    walkins INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tgt_events_start ON tgt_events(starts_at);
CREATE TABLE IF NOT EXISTS tgt_event_regs (
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL,
    reminded INTEGER NOT NULL DEFAULT 0,
    attended INTEGER NOT NULL DEFAULT 0,
    rating INTEGER,
    rating_asked INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (event_id, user_id)
);
CREATE TABLE IF NOT EXISTS event_summary (
    event_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    starts_at INTEGER NOT NULL,
    registered INTEGER NOT NULL,
    attended INTEGER NOT NULL,
    walkins INTEGER NOT NULL,
    rating_sum INTEGER NOT NULL,
    rating_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    anonymous INTEGER NOT NULL DEFAULT 0,
    sender TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created INTEGER NOT NULL,
    answered INTEGER
);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    photo_id TEXT NOT NULL DEFAULT '',
    link TEXT NOT NULL DEFAULT '',
    notified INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_created ON news(created);
CREATE TABLE IF NOT EXISTS news_subs (
    user_id INTEGER PRIMARY KEY,
    created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position INTEGER NOT NULL,
    q_az TEXT NOT NULL,
    a_az TEXT NOT NULL,
    q_ru TEXT NOT NULL DEFAULT '',
    a_ru TEXT NOT NULL DEFAULT '',
    q_en TEXT NOT NULL DEFAULT '',
    a_en TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS muted (
    user_id INTEGER PRIMARY KEY,
    until INTEGER NOT NULL
);
"""

PERSON_COLUMNS = ("role", "first_name", "last_name", "patronymic", "phone", "email")


def init(path: str) -> None:
    global _conn
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.executescript(SCHEMA)
    _migrate()
    _conn.execute("DELETE FROM events WHERE ts < ?", (int(time.time()) - 90 * 86400,))
    _conn.commit()
    _purge_old(int(time.time()))


def _migrate() -> None:
    """Добавляет новые столбцы в таблицы, созданные прежними версиями бота (данные сохраняются)."""
    conn = _conn

    def columns(table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    if "walkins" not in columns("tgt_events"):
        conn.execute("ALTER TABLE tgt_events ADD COLUMN walkins INTEGER NOT NULL DEFAULT 0")
    regs = columns("tgt_event_regs")
    for name, ddl in (
        ("attended", "INTEGER NOT NULL DEFAULT 0"),
        ("rating", "INTEGER"),
        ("rating_asked", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if name not in regs:
            conn.execute(f"ALTER TABLE tgt_event_regs ADD COLUMN {name} {ddl}")
    conn.commit()


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


async def _call(fn, *args):
    def run():
        with _lock:
            return fn(*args)

    return await asyncio.to_thread(run)


def _db() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("База данных не инициализирована (db.init)")
    return _conn


# ---------- пользователи и статистика ----------

def _touch_user(uid: int, section: str | None) -> None:
    now = int(time.time())
    conn = _db()
    conn.execute(
        "INSERT INTO users(id, first_seen, last_seen) VALUES(?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen, blocked = 0",
        (uid, now, now),
    )
    if section:
        conn.execute("INSERT INTO events(section, ts) VALUES(?, ?)", (section, now))
    conn.commit()


def _log_event(section: str) -> None:
    conn = _db()
    conn.execute("INSERT INTO events(section, ts) VALUES(?, ?)", (section, int(time.time())))
    conn.commit()


def _set_lang(uid: int, lang: str) -> None:
    now = int(time.time())
    conn = _db()
    conn.execute(
        "INSERT INTO users(id, lang, first_seen, last_seen) VALUES(?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET lang = excluded.lang",
        (uid, lang, now, now),
    )
    conn.commit()


def _load_langs() -> dict[int, str]:
    rows = _db().execute("SELECT id, lang FROM users WHERE lang IS NOT NULL").fetchall()
    return {int(uid): lang for uid, lang in rows}


def _recipient_ids() -> list[int]:
    return [int(r[0]) for r in _db().execute("SELECT id FROM users WHERE blocked = 0").fetchall()]


def _mark_blocked(uid: int) -> None:
    conn = _db()
    conn.execute("UPDATE users SET blocked = 1 WHERE id = ?", (uid,))
    conn.commit()


def _get_stats() -> dict:
    conn = _db()
    now = int(time.time())

    def one(sql: str, params: tuple = ()) -> int:
        return int(conn.execute(sql, params).fetchone()[0])

    return {
        "total": one("SELECT COUNT(*) FROM users"),
        "active_24h": one("SELECT COUNT(*) FROM users WHERE last_seen >= ?", (now - 86400,)),
        "active_7d": one("SELECT COUNT(*) FROM users WHERE last_seen >= ?", (now - 7 * 86400,)),
        "blocked": one("SELECT COUNT(*) FROM users WHERE blocked = 1"),
        "langs": {
            (lang or "?"): int(cnt)
            for lang, cnt in conn.execute("SELECT lang, COUNT(*) FROM users GROUP BY lang").fetchall()
        },
        "top_sections": [
            (section, int(cnt))
            for section, cnt in conn.execute(
                "SELECT section, COUNT(*) AS c FROM events WHERE ts >= ? GROUP BY section ORDER BY c DESC",
                (now - 7 * 86400,),
            ).fetchall()
        ],
    }


# ---------- люди (сədr, müavin, команда TGT) ----------

def _load_people() -> dict[str, dict[str, str]]:
    rows = _db().execute(f"SELECT key, {', '.join(PERSON_COLUMNS)} FROM people").fetchall()
    return {row[0]: dict(zip(PERSON_COLUMNS, row[1:])) for row in rows}


def _save_person(key: str, record: dict[str, str]) -> None:
    conn = _db()
    values = [str(record.get(col, "")) for col in PERSON_COLUMNS]
    conn.execute(
        f"INSERT INTO people(key, {', '.join(PERSON_COLUMNS)}) VALUES(?, {', '.join('?' for _ in PERSON_COLUMNS)}) "
        f"ON CONFLICT(key) DO UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in PERSON_COLUMNS)}",
        [key, *values],
    )
    conn.commit()


# ---------- настройки (описания клубов, комната, адрес) ----------

def _kv_items(prefix: str) -> dict[str, str]:
    rows = _db().execute("SELECT key, value FROM kv WHERE substr(key, 1, ?) = ?", (len(prefix), prefix)).fetchall()
    return {k[len(prefix):]: v for k, v in rows}


def _kv_get(key: str) -> str | None:
    row = _db().execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def _kv_set(key: str, value: str) -> None:
    conn = _db()
    conn.execute(
        "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def _kv_delete(key: str) -> None:
    conn = _db()
    conn.execute("DELETE FROM kv WHERE key = ?", (key,))
    conn.commit()


async def touch_user(uid: int, section: str | None = None) -> None:
    await _call(_touch_user, uid, section)


async def log_event(section: str) -> None:
    await _call(_log_event, section)


async def set_lang(uid: int, lang: str) -> None:
    await _call(_set_lang, uid, lang)


async def load_langs() -> dict[int, str]:
    return await _call(_load_langs)


async def recipient_ids() -> list[int]:
    return await _call(_recipient_ids)


async def mark_blocked(uid: int) -> None:
    await _call(_mark_blocked, uid)


async def get_stats() -> dict:
    return await _call(_get_stats)


async def load_people() -> dict[str, dict[str, str]]:
    return await _call(_load_people)


async def save_person(key: str, record: dict[str, str]) -> None:
    await _call(_save_person, key, record)


async def kv_items(prefix: str) -> dict[str, str]:
    return await _call(_kv_items, prefix)


async def kv_get(key: str) -> str | None:
    return await _call(_kv_get, key)


async def kv_set(key: str, value: str) -> None:
    await _call(_kv_set, key, value)


async def kv_delete(key: str) -> None:
    await _call(_kv_delete, key)


# ======================================================================
# Заявки в клубы, мероприятия, обращения
# Персональные данные хранятся ограниченное время (см. _purge_old).
# ======================================================================

APP_OPEN_LIMIT = 5        # открытых заявок в клубы у одного человека
FB_OPEN_LIMIT = 3         # открытых обращений у одного человека
FB_COOLDOWN = 30          # секунд между обращениями
REMIND_BEFORE = 24 * 3600  # напоминание за сутки


def _dicts(sql: str, params: tuple = ()) -> list[dict]:
    cur = _db().execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _purge_old(now: int) -> None:
    """Удаляет устаревшие персональные данные: обработанные заявки и ответы (90 дней), прошедшие события (30 дней)."""
    conn = _db()
    conn.execute("DELETE FROM applications WHERE status != 'new' AND COALESCE(decided, created) < ?", (now - 90 * 86400,))
    conn.execute("DELETE FROM applications WHERE created < ?", (now - 365 * 86400,))
    conn.execute("DELETE FROM feedback WHERE status != 'new' AND COALESCE(answered, created) < ?", (now - 90 * 86400,))
    conn.execute("DELETE FROM feedback WHERE created < ?", (now - 365 * 86400,))
    # итоги прошедших мероприятий (без имён участников) сохраняются для отчётов
    for row in conn.execute(
        "SELECT e.id, e.title, e.starts_at, e.walkins, "
        "(SELECT COUNT(*) FROM tgt_event_regs r WHERE r.event_id = e.id), "
        "(SELECT COUNT(*) FROM tgt_event_regs r WHERE r.event_id = e.id AND r.attended = 1), "
        "(SELECT COALESCE(SUM(r.rating), 0) FROM tgt_event_regs r WHERE r.event_id = e.id), "
        "(SELECT COUNT(r.rating) FROM tgt_event_regs r WHERE r.event_id = e.id) "
        "FROM tgt_events e WHERE e.starts_at < ?",
        (now - 30 * 86400,),
    ).fetchall():
        conn.execute(
            "INSERT OR REPLACE INTO event_summary(event_id, title, starts_at, walkins, registered, attended, rating_sum, rating_count) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
    old = [r[0] for r in conn.execute("SELECT id FROM tgt_events WHERE starts_at < ?", (now - 30 * 86400,)).fetchall()]
    for event_id in old:
        conn.execute("DELETE FROM tgt_event_regs WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM tgt_events WHERE id = ?", (event_id,))
    conn.execute("DELETE FROM muted WHERE until < ?", (now,))
    conn.commit()


# ---------- заявки в клубы ----------

def _application_precheck(user_id: int, club: str) -> str | None:
    conn = _db()
    if conn.execute("SELECT 1 FROM applications WHERE user_id = ? AND club = ? AND status = 'new'", (user_id, club)).fetchone():
        return "duplicate"
    if conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'new'", (user_id,)).fetchone()[0] >= APP_OPEN_LIMIT:
        return "limit"
    return None


def _add_application(club, user_id, name, faculty, phone, username, now) -> tuple[int | None, str | None]:
    error = _application_precheck(user_id, club)
    if error:
        return None, error
    conn = _db()
    cur = conn.execute(
        "INSERT INTO applications(club, user_id, name, faculty, phone, username, created) VALUES(?, ?, ?, ?, ?, ?, ?)",
        (club, user_id, name, faculty, phone, username, now),
    )
    conn.commit()
    return int(cur.lastrowid), None


def _get_application(app_id: int) -> dict | None:
    rows = _dicts("SELECT * FROM applications WHERE id = ?", (app_id,))
    return rows[0] if rows else None


def _list_applications(status: str = "new", limit: int = 30) -> list[dict]:
    return _dicts("SELECT * FROM applications WHERE status = ? ORDER BY id LIMIT ?", (status, limit))


def _set_application_status(app_id: int, status: str, now: int) -> bool:
    conn = _db()
    cur = conn.execute("UPDATE applications SET status = ?, decided = ? WHERE id = ? AND status = 'new'", (status, now, app_id))
    conn.commit()
    return cur.rowcount > 0


def _count_applications(status: str = "new") -> int:
    return int(_db().execute("SELECT COUNT(*) FROM applications WHERE status = ?", (status,)).fetchone()[0])


# ---------- мероприятия ----------

_EVENT_SELECT = (
    "SELECT e.*, "
    "(SELECT COUNT(*) FROM tgt_event_regs r WHERE r.event_id = e.id) AS registered, "
    "(SELECT COUNT(*) FROM tgt_event_regs r WHERE r.event_id = e.id AND r.attended = 1) AS attended, "
    "(SELECT COUNT(r.rating) FROM tgt_event_regs r WHERE r.event_id = e.id) AS rating_n, "
    "(SELECT COALESCE(SUM(r.rating), 0) FROM tgt_event_regs r WHERE r.event_id = e.id) AS rating_sum "
    "FROM tgt_events e"
)


def _add_event(title, place, description, starts_at, capacity, now) -> int:
    conn = _db()
    cur = conn.execute(
        "INSERT INTO tgt_events(title, place, description, starts_at, capacity, created) VALUES(?, ?, ?, ?, ?, ?)",
        (title, place, description, starts_at, capacity, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def _get_event(event_id: int) -> dict | None:
    rows = _dicts(f"{_EVENT_SELECT} WHERE e.id = ?", (event_id,))
    return rows[0] if rows else None


def _list_events(since: int, limit: int = 50) -> list[dict]:
    return _dicts(f"{_EVENT_SELECT} WHERE e.starts_at >= ? ORDER BY e.starts_at, e.id LIMIT ?", (since, limit))


def _update_event(event_id: int, field: str, value) -> bool:
    if field not in ("title", "place", "description", "starts_at", "capacity"):
        raise ValueError(f"Недопустимое поле события: {field!r}")
    conn = _db()
    cur = conn.execute(f"UPDATE tgt_events SET {field} = ? WHERE id = ?", (value, event_id))
    if field == "starts_at":  # время изменилось: напоминания нужно отправить заново
        conn.execute("UPDATE tgt_event_regs SET reminded = 0 WHERE event_id = ?", (event_id,))
    conn.commit()
    return cur.rowcount > 0


def _delete_event(event_id: int) -> list[int]:
    """Удаляет событие и записи на него. Возвращает ID записанных (чтобы сообщить об отмене)."""
    conn = _db()
    users = [int(r[0]) for r in conn.execute("SELECT user_id FROM tgt_event_regs WHERE event_id = ?", (event_id,)).fetchall()]
    conn.execute("DELETE FROM tgt_event_regs WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM tgt_events WHERE id = ?", (event_id,))
    conn.commit()
    return users


def _set_event_notified(event_id: int) -> None:
    conn = _db()
    conn.execute("UPDATE tgt_events SET notified = 1 WHERE id = ?", (event_id,))
    conn.commit()


def _register(event_id: int, user_id: int, name: str, username: str, now: int) -> str:
    """'ok' | 'already' | 'full' | 'closed' | 'missing'. Проверка и запись выполняются атомарно (под общей блокировкой)."""
    event = _get_event(event_id)
    if event is None:
        return "missing"
    if event["starts_at"] <= now:
        return "closed"
    conn = _db()
    if conn.execute("SELECT 1 FROM tgt_event_regs WHERE event_id = ? AND user_id = ?", (event_id, user_id)).fetchone():
        return "already"
    if event["capacity"] is not None and event["registered"] >= event["capacity"]:
        return "full"
    reminded = 1 if event["starts_at"] - now <= REMIND_BEFORE else 0  # уже в окне напоминания: повторно напоминать не нужно
    conn.execute(
        "INSERT INTO tgt_event_regs(event_id, user_id, name, username, created, reminded) VALUES(?, ?, ?, ?, ?, ?)",
        (event_id, user_id, name, username, now, reminded),
    )
    conn.commit()
    return "ok"


def _unregister(event_id: int, user_id: int) -> bool:
    conn = _db()
    cur = conn.execute("DELETE FROM tgt_event_regs WHERE event_id = ? AND user_id = ?", (event_id, user_id))
    conn.commit()
    return cur.rowcount > 0


def _is_registered(event_id: int, user_id: int) -> bool:
    return _db().execute("SELECT 1 FROM tgt_event_regs WHERE event_id = ? AND user_id = ?", (event_id, user_id)).fetchone() is not None


def _list_registrations(event_id: int) -> list[dict]:
    return _dicts(
        "SELECT user_id, name, username, created, attended, rating FROM tgt_event_regs WHERE event_id = ? ORDER BY created, user_id",
        (event_id,),
    )


def _due_reminders(now: int) -> list[dict]:
    return _dicts(
        "SELECT r.event_id, r.user_id FROM tgt_event_regs r JOIN tgt_events e ON e.id = r.event_id "
        "WHERE r.reminded = 0 AND e.starts_at > ? AND e.starts_at - ? <= ?",
        (now, now, REMIND_BEFORE),
    )


def _mark_reminded(event_id: int, user_id: int) -> None:
    conn = _db()
    conn.execute("UPDATE tgt_event_regs SET reminded = 1 WHERE event_id = ? AND user_id = ?", (event_id, user_id))
    conn.commit()


def _count_upcoming_events(now: int) -> int:
    return int(_db().execute("SELECT COUNT(*) FROM tgt_events WHERE starts_at >= ?", (now,)).fetchone()[0])


# ---------- обращения (предложения, жалобы, вопросы) ----------

def _is_muted(user_id: int, now: int) -> bool:
    row = _db().execute("SELECT until FROM muted WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row and row[0] > now)


def _mute(user_id: int, until: int) -> None:
    conn = _db()
    conn.execute(
        "INSERT INTO muted(user_id, until) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET until = excluded.until",
        (user_id, until),
    )
    conn.commit()


def _feedback_precheck(user_id: int, now: int) -> str | None:
    conn = _db()
    if _is_muted(user_id, now):
        return "muted"
    last = conn.execute("SELECT MAX(created) FROM feedback WHERE user_id = ?", (user_id,)).fetchone()[0]
    if last is not None and now - last < FB_COOLDOWN:
        return "cooldown"
    if conn.execute("SELECT COUNT(*) FROM feedback WHERE user_id = ? AND status = 'new'", (user_id,)).fetchone()[0] >= FB_OPEN_LIMIT:
        return "limit"
    return None


def _add_feedback(user_id, kind, anonymous, sender, username, text, now) -> tuple[int | None, str | None]:
    error = _feedback_precheck(user_id, now)
    if error:
        return None, error
    conn = _db()
    cur = conn.execute(
        "INSERT INTO feedback(user_id, kind, anonymous, sender, username, text, created) VALUES(?, ?, ?, ?, ?, ?, ?)",
        (user_id, kind, 1 if anonymous else 0, "" if anonymous else sender, "" if anonymous else username, text, now),
    )
    conn.commit()
    return int(cur.lastrowid), None


def _get_feedback(feedback_id: int) -> dict | None:
    rows = _dicts("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
    return rows[0] if rows else None


def _list_feedback(status: str = "new", limit: int = 30) -> list[dict]:
    return _dicts("SELECT * FROM feedback WHERE status = ? ORDER BY id LIMIT ?", (status, limit))


def _set_feedback_status(feedback_id: int, status: str, now: int) -> bool:
    conn = _db()
    cur = conn.execute("UPDATE feedback SET status = ?, answered = ? WHERE id = ? AND status = 'new'", (status, now, feedback_id))
    conn.commit()
    return cur.rowcount > 0


def _count_feedback(status: str = "new") -> int:
    return int(_db().execute("SELECT COUNT(*) FROM feedback WHERE status = ?", (status,)).fetchone()[0])


# ---------- асинхронные обёртки ----------

async def purge_old(now: int | None = None) -> None:
    await _call(_purge_old, int(now if now is not None else time.time()))


async def application_precheck(user_id: int, club: str) -> str | None:
    return await _call(_application_precheck, user_id, club)


async def add_application(club, user_id, name, faculty, phone, username, now: int | None = None):
    return await _call(_add_application, club, user_id, name, faculty, phone, username, int(now if now is not None else time.time()))


async def get_application(app_id: int) -> dict | None:
    return await _call(_get_application, app_id)


async def list_applications(status: str = "new", limit: int = 30) -> list[dict]:
    return await _call(_list_applications, status, limit)


async def set_application_status(app_id: int, status: str, now: int | None = None) -> bool:
    return await _call(_set_application_status, app_id, status, int(now if now is not None else time.time()))


async def count_applications(status: str = "new") -> int:
    return await _call(_count_applications, status)


async def add_event(title, place, description, starts_at, capacity, now: int | None = None) -> int:
    return await _call(_add_event, title, place, description, starts_at, capacity, int(now if now is not None else time.time()))


async def get_event(event_id: int) -> dict | None:
    return await _call(_get_event, event_id)


async def list_events(since: int, limit: int = 50) -> list[dict]:
    return await _call(_list_events, since, limit)


async def update_event(event_id: int, field: str, value) -> bool:
    return await _call(_update_event, event_id, field, value)


async def delete_event(event_id: int) -> list[int]:
    return await _call(_delete_event, event_id)


async def set_event_notified(event_id: int) -> None:
    await _call(_set_event_notified, event_id)


async def register(event_id: int, user_id: int, name: str, username: str, now: int | None = None) -> str:
    return await _call(_register, event_id, user_id, name, username, int(now if now is not None else time.time()))


async def unregister(event_id: int, user_id: int) -> bool:
    return await _call(_unregister, event_id, user_id)


async def is_registered(event_id: int, user_id: int) -> bool:
    return await _call(_is_registered, event_id, user_id)


async def list_registrations(event_id: int) -> list[dict]:
    return await _call(_list_registrations, event_id)


async def due_reminders(now: int | None = None) -> list[dict]:
    return await _call(_due_reminders, int(now if now is not None else time.time()))


async def mark_reminded(event_id: int, user_id: int) -> None:
    await _call(_mark_reminded, event_id, user_id)


async def count_upcoming_events(now: int | None = None) -> int:
    return await _call(_count_upcoming_events, int(now if now is not None else time.time()))


async def feedback_precheck(user_id: int, now: int | None = None) -> str | None:
    return await _call(_feedback_precheck, user_id, int(now if now is not None else time.time()))


async def add_feedback(user_id, kind, anonymous, sender, username, text, now: int | None = None):
    return await _call(_add_feedback, user_id, kind, anonymous, sender, username, text, int(now if now is not None else time.time()))


async def get_feedback(feedback_id: int) -> dict | None:
    return await _call(_get_feedback, feedback_id)


async def list_feedback(status: str = "new", limit: int = 30) -> list[dict]:
    return await _call(_list_feedback, status, limit)


async def set_feedback_status(feedback_id: int, status: str, now: int | None = None) -> bool:
    return await _call(_set_feedback_status, feedback_id, status, int(now if now is not None else time.time()))


async def count_feedback(status: str = "new") -> int:
    return await _call(_count_feedback, status)


async def mute_user(user_id: int, until: int) -> None:
    await _call(_mute, user_id, until)


async def is_muted(user_id: int, now: int | None = None) -> bool:
    return await _call(_is_muted, user_id, int(now if now is not None else time.time()))


# ======================================================================
# Посещаемость, оценки мероприятий, отчёты
# ======================================================================

MAX_WALKINS = 10000


def _set_attendance(event_id: int, user_id: int, attended: bool) -> bool:
    conn = _db()
    cur = conn.execute(
        "UPDATE tgt_event_regs SET attended = ? WHERE event_id = ? AND user_id = ?", (1 if attended else 0, event_id, user_id)
    )
    conn.commit()
    return cur.rowcount > 0


def _set_all_attendance(event_id: int, attended: bool) -> int:
    conn = _db()
    cur = conn.execute("UPDATE tgt_event_regs SET attended = ? WHERE event_id = ?", (1 if attended else 0, event_id))
    conn.commit()
    return cur.rowcount


def _adjust_walkins(event_id: int, delta: int) -> int | None:
    """Меняет число пришедших без записи (не меньше 0). Возвращает новое значение или None, если события нет."""
    conn = _db()
    conn.execute(
        "UPDATE tgt_events SET walkins = MIN(?, MAX(0, walkins + ?)) WHERE id = ?", (MAX_WALKINS, int(delta), event_id)
    )
    conn.commit()
    row = conn.execute("SELECT walkins FROM tgt_events WHERE id = ?", (event_id,)).fetchone()
    return int(row[0]) if row else None


def _attendees_to_ask(event_id: int) -> list[int]:
    rows = _db().execute(
        "SELECT user_id FROM tgt_event_regs WHERE event_id = ? AND attended = 1 AND rating_asked = 0 AND rating IS NULL ORDER BY user_id",
        (event_id,),
    ).fetchall()
    return [int(r[0]) for r in rows]


def _mark_rating_asked(event_id: int, user_ids: list[int]) -> None:
    conn = _db()
    conn.executemany("UPDATE tgt_event_regs SET rating_asked = 1 WHERE event_id = ? AND user_id = ?", [(event_id, u) for u in user_ids])
    conn.commit()


def _set_rating(event_id: int, user_id: int, rating: int) -> str:
    """'ok' | 'already' | 'not_attended' | 'missing'. Оценить может только отмеченный как пришедший, один раз."""
    if not 1 <= rating <= 5:
        return "missing"
    conn = _db()
    row = conn.execute("SELECT attended, rating FROM tgt_event_regs WHERE event_id = ? AND user_id = ?", (event_id, user_id)).fetchone()
    if row is None:
        return "missing"
    if not row[0]:
        return "not_attended"
    if row[1] is not None:
        return "already"
    conn.execute("UPDATE tgt_event_regs SET rating = ? WHERE event_id = ? AND user_id = ?", (rating, event_id, user_id))
    conn.commit()
    return "ok"


def _report(now: int) -> list[dict]:
    """Итоги всех завершившихся мероприятий (и текущих, и уже архивных), новые первыми."""
    live = _dicts(f"{_EVENT_SELECT} WHERE e.starts_at <= ?", (now,))
    rows = [
        {
            "id": e["id"], "title": e["title"], "starts_at": e["starts_at"], "registered": e["registered"],
            "attended": e["attended"], "walkins": e["walkins"], "rating_sum": e["rating_sum"], "rating_n": e["rating_n"],
        }
        for e in live
    ]
    live_ids = {r["id"] for r in rows}
    for s in _dicts(
        "SELECT event_id AS id, title, starts_at, registered, attended, walkins, rating_sum, rating_count AS rating_n FROM event_summary"
    ):
        if s["id"] not in live_ids:
            rows.append(s)
    return sorted(rows, key=lambda r: r["starts_at"], reverse=True)


async def set_attendance(event_id: int, user_id: int, attended: bool) -> bool:
    return await _call(_set_attendance, event_id, user_id, attended)


async def set_all_attendance(event_id: int, attended: bool) -> int:
    return await _call(_set_all_attendance, event_id, attended)


async def adjust_walkins(event_id: int, delta: int) -> int | None:
    return await _call(_adjust_walkins, event_id, delta)


async def attendees_to_ask(event_id: int) -> list[int]:
    return await _call(_attendees_to_ask, event_id)


async def mark_rating_asked(event_id: int, user_ids: list[int]) -> None:
    await _call(_mark_rating_asked, event_id, user_ids)


async def set_rating(event_id: int, user_id: int, rating: int) -> str:
    return await _call(_set_rating, event_id, user_id, rating)


async def report(now: int | None = None) -> list[dict]:
    return await _call(_report, int(now if now is not None else time.time()))


# ======================================================================
# Новости TGT и подписка на уведомления о них
# ======================================================================

def _add_news(title: str, body: str, photo_id: str, link: str, now: int) -> int:
    conn = _db()
    cur = conn.execute("INSERT INTO news(title, body, photo_id, link, created) VALUES(?, ?, ?, ?, ?)", (title, body, photo_id, link, now))
    conn.commit()
    return int(cur.lastrowid)


def _get_news(news_id: int) -> dict | None:
    rows = _dicts("SELECT * FROM news WHERE id = ?", (news_id,))
    return rows[0] if rows else None


def _list_news(limit: int = 10) -> list[dict]:
    return _dicts("SELECT * FROM news ORDER BY created DESC, id DESC LIMIT ?", (limit,))


def _update_news(news_id: int, field: str, value: str) -> bool:
    if field not in ("title", "body", "photo_id", "link"):
        raise ValueError(f"Недопустимое поле новости: {field!r}")
    conn = _db()
    cur = conn.execute(f"UPDATE news SET {field} = ? WHERE id = ?", (value, news_id))
    conn.commit()
    return cur.rowcount > 0


def _delete_news(news_id: int) -> bool:
    conn = _db()
    cur = conn.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    return cur.rowcount > 0


def _set_news_notified(news_id: int) -> None:
    conn = _db()
    conn.execute("UPDATE news SET notified = 1 WHERE id = ?", (news_id,))
    conn.commit()


def _set_news_subscription(user_id: int, enabled: bool, now: int) -> None:
    conn = _db()
    conn.execute("INSERT INTO users(id, first_seen, last_seen) VALUES(?, ?, ?) ON CONFLICT(id) DO NOTHING", (user_id, now, now))
    if enabled:
        conn.execute("INSERT OR IGNORE INTO news_subs(user_id, created) VALUES(?, ?)", (user_id, now))
    else:
        conn.execute("DELETE FROM news_subs WHERE user_id = ?", (user_id,))
    conn.commit()


def _is_news_subscribed(user_id: int) -> bool:
    return _db().execute("SELECT 1 FROM news_subs WHERE user_id = ?", (user_id,)).fetchone() is not None


def _news_subscribers() -> list[int]:
    rows = _db().execute("SELECT s.user_id FROM news_subs s JOIN users u ON u.id = s.user_id WHERE u.blocked = 0 ORDER BY s.user_id").fetchall()
    return [int(r[0]) for r in rows]


async def add_news(title: str, body: str, photo_id: str, link: str, now: int | None = None) -> int:
    return await _call(_add_news, title, body, photo_id, link, int(now if now is not None else time.time()))


async def get_news(news_id: int) -> dict | None:
    return await _call(_get_news, news_id)


async def list_news(limit: int = 10) -> list[dict]:
    return await _call(_list_news, limit)


async def update_news(news_id: int, field: str, value: str) -> bool:
    return await _call(_update_news, news_id, field, value)


async def delete_news(news_id: int) -> bool:
    return await _call(_delete_news, news_id)


async def set_news_notified(news_id: int) -> None:
    await _call(_set_news_notified, news_id)


async def set_news_subscription(user_id: int, enabled: bool, now: int | None = None) -> None:
    await _call(_set_news_subscription, user_id, enabled, int(now if now is not None else time.time()))


async def is_news_subscribed(user_id: int) -> bool:
    return await _call(_is_news_subscribed, user_id)


async def news_subscribers() -> list[int]:
    return await _call(_news_subscribers)


# ======================================================================
# FAQ (часто задаваемые вопросы)
# ======================================================================

FAQ_FIELDS = ("q_az", "a_az", "q_ru", "a_ru", "q_en", "a_en")


def _add_faq(values: dict[str, str], now: int) -> int:
    conn = _db()
    position = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM faq").fetchone()[0]
    cols = [f for f in FAQ_FIELDS if f in values]
    cur = conn.execute(
        f"INSERT INTO faq(position, created, {', '.join(cols)}) VALUES(?, ?, {', '.join('?' for _ in cols)})",
        [position, now, *[values[c] for c in cols]],
    )
    conn.commit()
    return int(cur.lastrowid)


def _get_faq(faq_id: int) -> dict | None:
    rows = _dicts("SELECT * FROM faq WHERE id = ?", (faq_id,))
    return rows[0] if rows else None


def _list_faq() -> list[dict]:
    return _dicts("SELECT * FROM faq ORDER BY position, id")


def _update_faq(faq_id: int, field: str, value: str) -> bool:
    if field not in FAQ_FIELDS:
        raise ValueError(f"Недопустимое поле FAQ: {field!r}")
    conn = _db()
    cur = conn.execute(f"UPDATE faq SET {field} = ? WHERE id = ?", (value, faq_id))
    conn.commit()
    return cur.rowcount > 0


def _delete_faq(faq_id: int) -> bool:
    conn = _db()
    cur = conn.execute("DELETE FROM faq WHERE id = ?", (faq_id,))
    conn.commit()
    return cur.rowcount > 0


def _move_faq(faq_id: int, direction: int) -> bool:
    """Меняет вопрос местами с соседним (direction: -1 вверх, +1 вниз). False, если двигать некуда."""
    ids = [item["id"] for item in _list_faq()]
    if faq_id not in ids:
        return False
    index = ids.index(faq_id)
    other = index + (-1 if direction < 0 else 1)
    if not 0 <= other < len(ids):
        return False
    ids[index], ids[other] = ids[other], ids[index]
    conn = _db()
    for position, fid in enumerate(ids, 1):  # позиции всегда подряд: порядок однозначен
        conn.execute("UPDATE faq SET position = ? WHERE id = ?", (position, fid))
    conn.commit()
    return True


def _faq_questions(ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    marks = ", ".join("?" for _ in ids)
    return {int(r[0]): r[1] for r in _db().execute(f"SELECT id, q_az FROM faq WHERE id IN ({marks})", ids).fetchall()}


def _faq_count() -> int:
    return int(_db().execute("SELECT COUNT(*) FROM faq").fetchone()[0])


async def add_faq(values: dict[str, str], now: int | None = None) -> int:
    return await _call(_add_faq, values, int(now if now is not None else time.time()))


async def get_faq(faq_id: int) -> dict | None:
    return await _call(_get_faq, faq_id)


async def list_faq() -> list[dict]:
    return await _call(_list_faq)


async def update_faq(faq_id: int, field: str, value: str) -> bool:
    return await _call(_update_faq, faq_id, field, value)


async def delete_faq(faq_id: int) -> bool:
    return await _call(_delete_faq, faq_id)


async def move_faq(faq_id: int, direction: int) -> bool:
    return await _call(_move_faq, faq_id, direction)


async def faq_questions(ids: list[int]) -> dict[int, str]:
    return await _call(_faq_questions, ids)


async def faq_count() -> int:
    return await _call(_faq_count)

