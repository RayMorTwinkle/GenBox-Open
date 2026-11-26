"""Append-only SQLite documents and revisions."""
import os
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 1024 * 1024
FORMATS = {".html": "html", ".htm": "html", ".md": "markdown",
           ".markdown": "markdown", ".svg": "svg"}


def read_source(path):
    format_name = FORMATS.get(path.suffix.lower())
    if not format_name:
        raise ValueError("支持 HTML、Markdown 和 SVG 文件。")
    with path.open("rb") as fh:
        raw = fh.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("单个文件上限为 1 MiB。")
    if not raw:
        raise ValueError("文件为空。")
    return format_name, raw.decode("utf-8-sig")


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.path = self.directory / "library.sqlite3"

    @contextmanager
    def connection(self, readonly=False):
        uri = self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw")
        with closing(sqlite3.connect(uri, uri=True, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            with conn:
                yield conn

    def initialize(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS items (
                    slug TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    slug TEXT NOT NULL REFERENCES items(slug),
                    version INTEGER NOT NULL CHECK (version >= 1),
                    title TEXT NOT NULL,
                    format TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    restored_from INTEGER,
                    PRIMARY KEY(slug, version)
                );
            """)

    @staticmethod
    def _head(conn, slug):
        row = conn.execute(
            "SELECT version,title FROM revisions WHERE slug=? ORDER BY version DESC LIMIT 1",
            (slug,),
        ).fetchone()
        if row is None:
            raise ValueError("找不到这个短链。")
        return row

    @staticmethod
    def _append(conn, slug, version, title, format_name, body, restored_from=None):
        title = title.strip()
        if not title or len(title) > 160:
            raise ValueError("标题长度应为 1 至 160 个字符。")
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO revisions VALUES (?,?,?,?,?,?,?)",
            (slug, version, title, format_name, body, created, restored_from),
        )
        return {"slug": slug, "version": version, "title": title, "format": format_name,
                "path": "/s/" + slug, "revision_path": f"/s/{slug}?v={version}"}

    def publish(self, file, slug=None, title=None):
        format_name, body = read_source(file)
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if slug is None:
                while True:
                    slug = secrets.token_urlsafe(8)
                    if conn.execute("INSERT OR IGNORE INTO items VALUES (?)", (slug,)).rowcount:
                        break
                version, previous_title = 1, file.stem
            else:
                head = self._head(conn, slug)
                version, previous_title = head["version"] + 1, head["title"]
            return self._append(conn, slug, version, previous_title if title is None else title,
                                format_name, body)

    def restore(self, slug, version):
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            head = self._head(conn, slug)
            old = conn.execute(
                "SELECT * FROM revisions WHERE slug=? AND version=?", (slug, version)
            ).fetchone()
            if old is None:
                raise ValueError("找不到这个版本。")
            return self._append(conn, slug, head["version"] + 1, old["title"],
                                old["format"], old["body"], old["version"])

    def read(self, slug, version=None):
        with self.connection(readonly=True) as conn:
            if version is None:
                row = conn.execute(
                    "SELECT * FROM revisions WHERE slug=? ORDER BY version DESC LIMIT 1", (slug,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM revisions WHERE slug=? AND version=?", (slug, version)
                ).fetchone()
        return dict(row) if row else None

    def history(self, slug):
        with self.connection(readonly=True) as conn:
            self._head(conn, slug)
            rows = conn.execute("""
                SELECT version,title,format,created_at,restored_from FROM revisions
                WHERE slug=? ORDER BY version DESC
            """, (slug,))
            return [dict(r) for r in rows]

    def items(self):
        with self.connection(readonly=True) as conn:
            rows = conn.execute("""
                SELECT r.slug,r.version,r.title,r.format,r.created_at FROM revisions r
                JOIN (SELECT slug,MAX(version) AS version FROM revisions GROUP BY slug) h
                ON h.slug=r.slug AND h.version=r.version
                ORDER BY r.rowid DESC
            """)
            return [dict(r) for r in rows]
