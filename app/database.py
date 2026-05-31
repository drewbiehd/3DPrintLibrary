import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / ".3dprintlibrary" / "library.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                format TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                date_added TEXT DEFAULT CURRENT_TIMESTAMP,
                category TEXT DEFAULT 'Uncategorized',
                tags TEXT DEFAULT '',
                thumbnail_path TEXT,
                custom_name TEXT,
                notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS watch_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')


def get_all_files(category=None, search=None):
    with get_connection() as conn:
        query = "SELECT * FROM files WHERE 1=1"
        params = []
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (filename LIKE ? OR custom_name LIKE ? OR tags LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        query += " ORDER BY date_added DESC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def upsert_file(path, filename, fmt, size, category, thumbnail_path=None):
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO files (path, filename, format, size, category, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename = excluded.filename,
                size = excluded.size,
                category = CASE WHEN category = 'Uncategorized' OR category IS NULL
                                THEN excluded.category ELSE category END,
                thumbnail_path = COALESCE(excluded.thumbnail_path, thumbnail_path)
        ''', (path, filename, fmt, size, category, thumbnail_path))


def update_file_category(file_id, category):
    with get_connection() as conn:
        conn.execute("UPDATE files SET category=? WHERE id=?", (category, file_id))


def update_file_thumbnail(path, thumbnail_path):
    with get_connection() as conn:
        conn.execute("UPDATE files SET thumbnail_path=? WHERE path=?", (thumbnail_path, path))


def update_file_notes(file_id, notes):
    with get_connection() as conn:
        conn.execute("UPDATE files SET notes=? WHERE id=?", (notes, file_id))


def update_custom_name(file_id, name):
    with get_connection() as conn:
        conn.execute("UPDATE files SET custom_name=? WHERE id=?", (name, file_id))


def get_categories():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as count FROM files GROUP BY category ORDER BY category"
        ).fetchall()
        return [dict(r) for r in rows]


def get_watch_folders():
    with get_connection() as conn:
        return [r["path"] for r in conn.execute("SELECT path FROM watch_folders").fetchall()]


def add_watch_folder(path):
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO watch_folders (path) VALUES (?)", (path,))


def remove_watch_folder(path):
    with get_connection() as conn:
        conn.execute("DELETE FROM watch_folders WHERE path=?", (path,))


def get_setting(key, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )


def remove_missing_files():
    with get_connection() as conn:
        paths = [r["path"] for r in conn.execute("SELECT path FROM files").fetchall()]
        missing = [p for p in paths if not Path(p).exists()]
        if missing:
            conn.executemany("DELETE FROM files WHERE path=?", [(p,) for p in missing])
        return len(missing)


def delete_file(file_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))


def get_configured_slicers():
    raw = get_setting("slicers", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_slicers(slicers):
    set_setting("slicers", json.dumps(slicers))
