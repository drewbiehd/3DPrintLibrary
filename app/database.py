import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / ".3dprintlibrary" / "library.db"

# ── Built-in category hierarchy ───────────────────────────────────────────────
# (parent_name, child_name_or_None, icon, color)
BUILTIN_CATEGORIES = [
    # Top-level
    ("Tools",               None, "🔧", "#e8873a"),
    ("Toys",                None, "🚗", "#66c0f4"),
    ("Gaming & Tabletop",   None, "🎲", "#9b7fd4"),
    ("Cosplay & Props",     None, "⚔",  "#e05c99"),
    ("Household",           None, "🏠", "#5ba85a"),
    ("Art & Decor",         None, "🎨", "#e8c43a"),
    ("Gadgets & Electronics", None, "💡", "#3ab8e8"),
    ("Utility",             None, "📦", "#4a9e7a"),
    ("Outdoors & Garden",   None, "🌿", "#7ab85a"),
    ("Fashion & Jewelry",   None, "💎", "#e87ab3"),
    ("3D Printer Parts",    None, "🖨", "#e87a3a"),
    ("Education",           None, "📚", "#5a9be8"),
    ("Repairs",             None, "🔩", "#e05c5c"),
    ("Uncategorized",       None, "📁", "#8f98a0"),
    # Toys sub-categories
    ("Clicker Toys",        "Toys", "🖱", "#b3a0d6"),
    ("Flexi & Articulated", "Toys", "🐍", "#7ab8e8"),
    ("Action Figures",      "Toys", "🤺", "#66c0f4"),
    ("Vehicles",            "Toys", "🚗", "#66c0f4"),
    ("Puzzles",             "Toys", "🧩", "#66c0f4"),
    ("Animals & Creatures", "Toys", "🦕", "#66c0f4"),
    # Gaming sub-categories
    ("Miniatures",          "Gaming & Tabletop", "⚔",  "#9b7fd4"),
    ("Terrain & Scenery",   "Gaming & Tabletop", "🏔", "#9b7fd4"),
    ("Dice & Accessories",  "Gaming & Tabletop", "🎲", "#9b7fd4"),
    ("Board Game Inserts",  "Gaming & Tabletop", "🎮", "#9b7fd4"),
    # Cosplay sub-categories
    ("Weapons & Props",     "Cosplay & Props", "⚔",  "#e05c99"),
    ("Armor & Wearables",   "Cosplay & Props", "🛡", "#e05c99"),
    ("Movie & TV",          "Cosplay & Props", "🎬", "#e05c99"),
    # Household sub-categories
    ("Kitchen",             "Household", "🍳", "#5ba85a"),
    ("Bathroom",            "Household", "🚿", "#5ba85a"),
    ("Storage & Org",       "Household", "📦", "#5ba85a"),
    ("Garage & Workshop",   "Household", "🔨", "#5ba85a"),
    # Art sub-categories
    ("Sculptures & Busts",  "Art & Decor", "🗿", "#e8c43a"),
    ("Wall Art",            "Art & Decor", "🖼",  "#e8c43a"),
    ("Vases & Planters",    "Art & Decor", "🌸", "#e8c43a"),
    # Tools sub-categories
    ("Hand Tools",          "Tools", "🔧", "#e8873a"),
    ("Workshop & Jigs",     "Tools", "🛠", "#e8873a"),
    ("Measuring",           "Tools", "📏", "#e8873a"),
    # 3D Printer Parts sub-categories
    ("Bambu / Orca",        "3D Printer Parts", "🖨", "#e87a3a"),
    ("Prusa",               "3D Printer Parts", "🖨", "#e87a3a"),
    ("Creality / Ender",    "3D Printer Parts", "🖨", "#e87a3a"),
    ("Voron",               "3D Printer Parts", "🖨", "#e87a3a"),
    ("General Upgrades",    "3D Printer Parts", "⚙",  "#e87a3a"),
    # Gadgets sub-categories
    ("Phone & Tablet",      "Gadgets & Electronics", "📱", "#3ab8e8"),
    ("PC & Peripherals",    "Gadgets & Electronics", "💻", "#3ab8e8"),
    ("Arduino & Pi",        "Gadgets & Electronics", "⚡", "#3ab8e8"),
    ("Audio",               "Gadgets & Electronics", "🔊", "#3ab8e8"),
]


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                parent_id   INTEGER DEFAULT NULL
                                REFERENCES categories(id) ON DELETE SET NULL,
                color       TEXT    DEFAULT "#8f98a0",
                icon        TEXT    DEFAULT "📁",
                sort_order  INTEGER DEFAULT 0,
                is_builtin  INTEGER DEFAULT 1,
                UNIQUE(name, parent_id)
            );

            CREATE TABLE IF NOT EXISTS files (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                path            TEXT    UNIQUE NOT NULL,
                filename        TEXT    NOT NULL,
                format          TEXT    NOT NULL,
                size            INTEGER DEFAULT 0,
                date_added      TEXT    DEFAULT CURRENT_TIMESTAMP,
                category        TEXT    DEFAULT "Uncategorized",
                subcategory     TEXT    DEFAULT "",
                tags            TEXT    DEFAULT "",
                thumbnail_path  TEXT,
                custom_name     TEXT,
                notes           TEXT    DEFAULT ""
            );

            CREATE TABLE IF NOT EXISTS watch_folders (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        ''')

        # Add subcategory column if upgrading from an older DB
        cols = [r[1] for r in conn.execute("PRAGMA table_info(files)").fetchall()]
        if "subcategory" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN subcategory TEXT DEFAULT ''")

    _init_builtin_categories()
    _migrate_legacy_categories()


def _init_builtin_categories():
    """Populate the categories table with built-ins (idempotent)."""
    with get_connection() as conn:
        # Build a name→id map for parents already inserted
        def _id(name):
            row = conn.execute(
                "SELECT id FROM categories WHERE name=? AND parent_id IS NULL", (name,)
            ).fetchone()
            return row["id"] if row else None

        sort = 0
        for name, parent_name, icon, color in BUILTIN_CATEGORIES:
            parent_id = _id(parent_name) if parent_name else None
            conn.execute(
                """INSERT OR IGNORE INTO categories (name, parent_id, icon, color, sort_order, is_builtin)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (name, parent_id, icon, color, sort),
            )
            sort += 1


def _migrate_legacy_categories():
    """Move files that used the old flat 'Clicker Toys' category
    to category='Toys', subcategory='Clicker Toys'."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE files SET category='Toys', subcategory='Clicker Toys' "
            "WHERE category='Clicker Toys' AND (subcategory IS NULL OR subcategory='')"
        )


# ── Category CRUD ─────────────────────────────────────────────────────────────

def get_category_tree() -> list[dict]:
    """
    Return the full hierarchy as a list of dicts:
      [{ id, name, icon, color, is_builtin,
         count,        ← files with this as parent (all subs)
         subcategories: [{ id, name, icon, color, count, is_builtin }] }]
    """
    with get_connection() as conn:
        # Count files per (category, subcategory)
        counts_raw = conn.execute(
            "SELECT category, subcategory, COUNT(*) as n FROM files GROUP BY category, subcategory"
        ).fetchall()
        # parent count = sum over all subcategories (including blank)
        parent_counts: dict[str, int] = {}
        sub_counts: dict[tuple, int] = {}
        for r in counts_raw:
            cat, sub, n = r["category"], r["subcategory"] or "", r["n"]
            parent_counts[cat] = parent_counts.get(cat, 0) + n
            sub_counts[(cat, sub)] = n

        parents = conn.execute(
            "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order, name"
        ).fetchall()

        tree = []
        for p in parents:
            children_rows = conn.execute(
                "SELECT * FROM categories WHERE parent_id=? ORDER BY sort_order, name",
                (p["id"],),
            ).fetchall()
            children = [
                {
                    "id":         c["id"],
                    "name":       c["name"],
                    "icon":       c["icon"],
                    "color":      c["color"],
                    "is_builtin": c["is_builtin"],
                    "count":      sub_counts.get((p["name"], c["name"]), 0),
                }
                for c in children_rows
            ]
            tree.append({
                "id":             p["id"],
                "name":           p["name"],
                "icon":           p["icon"],
                "color":          p["color"],
                "is_builtin":     p["is_builtin"],
                "count":          parent_counts.get(p["name"], 0),
                "subcategories":  children,
            })
        return tree


def add_category(name: str, parent_id: int | None,
                 icon: str = "📁", color: str = "#8f98a0") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO categories (name, parent_id, icon, color, is_builtin) "
            "VALUES (?, ?, ?, ?, 0)",
            (name, parent_id, icon, color),
        )
        return cur.lastrowid


def rename_category(cat_id: int, new_name: str):
    with get_connection() as conn:
        # Get old name + parent to update files table too
        row = conn.execute(
            "SELECT c.name, p.name as parent_name "
            "FROM categories c LEFT JOIN categories p ON c.parent_id=p.id "
            "WHERE c.id=?", (cat_id,)
        ).fetchone()
        if not row:
            return
        old_name, parent_name = row["name"], row["parent_name"]

        conn.execute("UPDATE categories SET name=? WHERE id=?", (new_name, cat_id))

        if parent_name:
            # It's a subcategory — update files.subcategory
            conn.execute(
                "UPDATE files SET subcategory=? WHERE category=? AND subcategory=?",
                (new_name, parent_name, old_name),
            )
        else:
            # It's a parent — update files.category (and child categories' parent refs stay by id)
            conn.execute(
                "UPDATE files SET category=? WHERE category=?", (new_name, old_name)
            )


def delete_category(cat_id: int):
    """
    Delete a category.  Files in it move to:
      - parent category (subcategory cleared) if deleting a sub-category
      - 'Uncategorized' if deleting a top-level category
    Child categories of a deleted parent are promoted to top-level (parent_id=NULL).
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT c.name, c.parent_id, p.name as parent_name "
            "FROM categories c LEFT JOIN categories p ON c.parent_id=p.id "
            "WHERE c.id=?", (cat_id,)
        ).fetchone()
        if not row:
            return
        name, parent_id, parent_name = row["name"], row["parent_id"], row["parent_name"]

        if parent_id:
            # Deleting a subcategory — clear subcategory on affected files
            conn.execute(
                "UPDATE files SET subcategory='' WHERE category=? AND subcategory=?",
                (parent_name, name),
            )
        else:
            # Deleting a parent — reassign files to Uncategorized
            conn.execute(
                "UPDATE files SET category='Uncategorized', subcategory='' WHERE category=?",
                (name,),
            )
            # Promote children to top-level
            conn.execute(
                "UPDATE categories SET parent_id=NULL WHERE parent_id=?", (cat_id,)
            )

        conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))


def update_category_style(cat_id: int, icon: str, color: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE categories SET icon=?, color=? WHERE id=?", (icon, color, cat_id)
        )


def reorder_category(cat_id: int, new_sort: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE categories SET sort_order=? WHERE id=?", (new_sort, cat_id)
        )


# ── Files ─────────────────────────────────────────────────────────────────────

def get_all_files(category: str | None = None,
                  subcategory: str | None = None,
                  search: str | None = None) -> list[dict]:
    with get_connection() as conn:
        q = "SELECT * FROM files WHERE 1=1"
        p: list = []
        if category and category != "All":
            q += " AND category=?"
            p.append(category)
        if subcategory:
            q += " AND subcategory=?"
            p.append(subcategory)
        if search:
            q += " AND (filename LIKE ? OR custom_name LIKE ? OR tags LIKE ?)"
            p += [f"%{search}%"] * 3
        q += " ORDER BY date_added DESC"
        return [dict(r) for r in conn.execute(q, p).fetchall()]


def upsert_file(path, filename, fmt, size, category, subcategory="", thumbnail_path=None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO files (path, filename, format, size, category, subcategory, thumbnail_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET
                   filename       = excluded.filename,
                   size           = excluded.size,
                   category       = CASE WHEN category IN ('Uncategorized','') OR category IS NULL
                                         THEN excluded.category ELSE category END,
                   subcategory    = CASE WHEN subcategory IS NULL OR subcategory = ''
                                         THEN excluded.subcategory ELSE subcategory END,
                   thumbnail_path = COALESCE(excluded.thumbnail_path, thumbnail_path)""",
            (path, filename, fmt, size, category, subcategory, thumbnail_path),
        )


def update_file_category(file_id: int, category: str, subcategory: str = ""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE files SET category=?, subcategory=? WHERE id=?",
            (category, subcategory, file_id),
        )


def update_file_thumbnail(path: str, thumbnail_path: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE files SET thumbnail_path=? WHERE path=?", (thumbnail_path, path)
        )


def update_file_notes(file_id: int, notes: str):
    with get_connection() as conn:
        conn.execute("UPDATE files SET notes=? WHERE id=?", (notes, file_id))


def update_custom_name(file_id: int, name: str):
    with get_connection() as conn:
        conn.execute("UPDATE files SET custom_name=? WHERE id=?", (name, file_id))


def get_watch_folders() -> list[str]:
    with get_connection() as conn:
        return [r["path"] for r in conn.execute("SELECT path FROM watch_folders").fetchall()]


def add_watch_folder(path: str):
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO watch_folders (path) VALUES (?)", (path,))


def remove_watch_folder(path: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM watch_folders WHERE path=?", (path,))


def get_setting(key: str, default=None) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )


def remove_missing_files() -> int:
    with get_connection() as conn:
        paths = [r["path"] for r in conn.execute("SELECT path FROM files").fetchall()]
        missing = [p for p in paths if not Path(p).exists()]
        if missing:
            conn.executemany("DELETE FROM files WHERE path=?", [(p,) for p in missing])
        return len(missing)


def delete_file(file_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))


def get_configured_slicers() -> list[dict]:
    raw = get_setting("slicers", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_slicers(slicers: list[dict]):
    set_setting("slicers", json.dumps(slicers))
