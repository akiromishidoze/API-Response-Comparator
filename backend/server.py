"""HTTP server for API Response Comparator.

Endpoints:
  GET  /                   → static frontend
  GET  /<static>           → any file under ../frontend
  GET  /api/health         → { "ok": true }
  POST /api/compare        → run a diff and append to history
  GET  /api/history        → list history entries (newest first)
  GET  /api/history/<id>   → fetch full entry
  DELETE /api/history/<id> → delete entry
  POST /api/export/html    → returns HTML file
  POST /api/export/pdf     → returns PDF file (needs reportlab)
"""

from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from differ import diff_lines, normalize, summarize  # noqa: E402
from exporter import to_html, to_pdf  # noqa: E402

FRONTEND = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "history.db"

HOST = "127.0.0.1"
PORT = 5175


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                format TEXT NOT NULL,
                ignore_json TEXT NOT NULL,
                left_raw TEXT NOT NULL,
                right_raw TEXT NOT NULL,
                rows_json TEXT NOT NULL,
                summary_json TEXT NOT NULL
            )
        """)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_from_row(row: sqlite3.Row, with_rows: bool = True) -> dict:
    out = {
        "id": row["id"],
        "created_at": row["created_at"],
        "title": row["title"],
        "format": row["format"],
        "ignore": json.loads(row["ignore_json"]),
        "summary": json.loads(row["summary_json"]),
    }
    if with_rows:
        out["rows"] = json.loads(row["rows_json"])
        out["left_raw"] = row["left_raw"]
        out["right_raw"] = row["right_raw"]
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "APIRespComp/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, status: int, body: bytes, content_type: str, filename: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (FRONTEND / path.lstrip("/")).resolve()
        try:
            target.relative_to(FRONTEND.resolve())
        except ValueError:
            self._json(403, {"error": "forbidden"})
            return
        if not target.is_file():
            self._json(404, {"error": "not found", "path": path})
            return
        ctype, _ = mimetypes.guess_type(str(target))
        self._file(200, target.read_bytes(), ctype or "application/octet-stream")

    def do_GET(self) -> None:
        url = urlparse(self.path)
        p = url.path

        if p == "/api/health":
            self._json(200, {"ok": True})
            return

        if p == "/api/history":
            with db() as c:
                rows = c.execute(
                    "SELECT * FROM history ORDER BY created_at DESC LIMIT 200"
                ).fetchall()
            self._json(200, [record_from_row(r, with_rows=False) for r in rows])
            return

        if p.startswith("/api/history/"):
            hid = p.rsplit("/", 1)[-1]
            with db() as c:
                row = c.execute("SELECT * FROM history WHERE id = ?", (hid,)).fetchone()
            if not row:
                self._json(404, {"error": "not found"})
                return
            self._json(200, record_from_row(row))
            return

        self._serve_static(p)

    def do_DELETE(self) -> None:
        url = urlparse(self.path)
        if url.path.startswith("/api/history/"):
            hid = url.path.rsplit("/", 1)[-1]
            with db() as c:
                c.execute("DELETE FROM history WHERE id = ?", (hid,))
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        url = urlparse(self.path)
        p = url.path

        if p == "/api/compare":
            data = self._read_json()
            left_raw = data.get("left", "")
            right_raw = data.get("right", "")
            fmt = (data.get("format") or "text").lower()
            ignore = data.get("ignore") or []
            title = (data.get("title") or "Untitled comparison").strip()[:200]
            save = bool(data.get("save", True))

            try:
                left_norm = normalize(left_raw, fmt, ignore)
                right_norm = normalize(right_raw, fmt, ignore)
            except ValueError as e:
                self._json(400, {"error": str(e)})
                return

            rows = diff_lines(left_norm, right_norm)
            summary = summarize(rows)
            record = {
                "id": uuid.uuid4().hex[:12],
                "created_at": now_iso(),
                "title": title,
                "format": fmt,
                "ignore": ignore,
                "left_raw": left_raw,
                "right_raw": right_raw,
                "left_normalized": left_norm,
                "right_normalized": right_norm,
                "rows": rows,
                "summary": summary,
            }

            if save:
                with db() as c:
                    c.execute(
                        "INSERT INTO history (id, created_at, title, format, ignore_json, "
                        "left_raw, right_raw, rows_json, summary_json) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            record["id"], record["created_at"], record["title"], fmt,
                            json.dumps(ignore), left_raw, right_raw,
                            json.dumps(rows), json.dumps(summary),
                        ),
                    )
            self._json(200, record)
            return

        if p == "/api/export/html":
            record = self._load_record_from_request()
            if record is None:
                return
            html_bytes = to_html(record).encode("utf-8")
            fname = _safe_filename(record["title"], "html")
            self._file(200, html_bytes, "text/html; charset=utf-8", fname)
            return

        if p == "/api/export/pdf":
            record = self._load_record_from_request()
            if record is None:
                return
            try:
                pdf_bytes = to_pdf(record)
            except RuntimeError as e:
                self._json(501, {"error": str(e)})
                return
            fname = _safe_filename(record["title"], "pdf")
            self._file(200, pdf_bytes, "application/pdf", fname)
            return

        self._json(404, {"error": "not found"})

    def _load_record_from_request(self) -> dict | None:
        """Accept either {id: '...'} referring to history, or a full record."""
        data = self._read_json()
        if data.get("id") and not data.get("rows"):
            with db() as c:
                row = c.execute(
                    "SELECT * FROM history WHERE id = ?", (data["id"],)
                ).fetchone()
            if not row:
                self._json(404, {"error": "history entry not found"})
                return None
            return record_from_row(row)
        if not data.get("rows"):
            self._json(400, {"error": "missing rows or id"})
            return None
        data.setdefault("created_at", now_iso())
        data.setdefault("title", "API Response Comparison")
        data.setdefault("format", "text")
        data.setdefault("ignore", [])
        return data


def _safe_filename(title: str, ext: str) -> str:
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in title).strip("_") or "diff"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base}-{stamp}.{ext}"


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"API Response Comparator running at {url}")
    print(f"DB: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
