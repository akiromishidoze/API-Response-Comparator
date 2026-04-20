# API Response Comparator

A side-by-side diff tool for API responses — paste in two payloads, mask out the fields that always change (timestamps, request IDs), and see exactly what's different. Supports **JSON**, **XML**, and **plain text**. Ships as a Linux desktop app with a local browser UI.

- Side-by-side diff with color coding (added / removed / changed / equal)
- Ignore-list for dynamic fields so noise doesn't flood the diff
- Every comparison is saved to a searchable history log
- Export any diff as a self-contained HTML file or a PDF report

## Requirements

- Python 3.10+
- A modern browser (the UI runs locally)
- Optional: `reportlab` for PDF export — install with `pip install -r requirements.txt`

No Node/npm needed — the frontend is plain HTML/CSS/JS served by the Python backend.

## Quick start

```bash
cd "API Response Comparator"
pip install -r requirements.txt    # optional, only for PDF export
python3 backend/server.py
```

Open http://127.0.0.1:5175/ in your browser.

## Desktop app (Linux) — one click, no terminal

Install once:

```bash
cd "/path/to/API Response Comparator"
./install-launcher.sh
```

Then find **API Response Comparator** in your app menu. Clicking it starts the backend and opens your browser to the UI. The backend keeps running until you kill it (`pkill -f "backend/server.py"`) or reboot.

To uninstall:

```bash
rm ~/.local/share/applications/api-response-comparator.desktop
rm ~/.local/share/icons/hicolor/scalable/apps/api-response-comparator.svg
```

## Using the UI

1. Pick a **Format** — JSON, XML, or Plain text.
2. Paste the baseline response into the **Left** pane and the new one into the **Right** pane (or use **Load file**).
3. Fill the **Ignore** field with keys/tags/regexes to mask — comma-separated. Examples:
   - JSON / XML: `timestamp, requestId, id, updated_at`
   - Plain text: regex patterns like `\d{4}-\d{2}-\d{2}T[\d:.]+Z` for ISO timestamps
4. Give the comparison a **Title** (optional — makes history easier to scan).
5. Click **Compare** (or `Ctrl+Enter`).

The diff table highlights:

| Color | Meaning |
|---|---|
| Green (+) | Line only on the right |
| Red (−) | Line only on the left |
| Yellow (~) | Line present on both sides but different |
| No color | Equal |

### Ignore-list behavior

- **JSON / XML:** masks any key or tag whose name matches a list entry — at any depth. The value is replaced with `<<IGNORED>>` before diffing, so matching keys always compare equal.
- **Plain text:** each entry is treated as a regex and replaced with `<<IGNORED>>`. If the regex is invalid, it falls back to a literal string replacement.

### History

Every comparison is saved automatically to `data/history.db` (SQLite). Click any entry in the left sidebar to re-load it into the editor. Hover and click `×` to delete it.

### Exports

- **Export HTML** — a self-contained `.html` file with all CSS inlined; open in any browser, share by email, print to PDF from the browser.
- **Export PDF** — generates a landscape PDF with the full diff. Requires `reportlab`.

## Project layout

```
API Response Comparator/
├── backend/
│   ├── server.py       # stdlib HTTP server + API routes
│   ├── differ.py       # normalize + line-diff for JSON, XML, text
│   └── exporter.py     # HTML + PDF rendering
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/               # runtime-only (history.db lives here; gitignored)
├── launch.sh           # starts backend, opens browser
├── install-launcher.sh # registers the .desktop entry
├── requirements.txt
└── README.md
```

## Notes

- The server binds to `127.0.0.1:5175` — localhost only, never your network.
- JSON normalization sorts keys and pretty-prints with 2-space indent, so key order differences don't show up as diffs.
- XML normalization re-serializes via `minidom` with 2-space indent. Whitespace-only differences are collapsed.
- History is capped at 200 most recent entries in the sidebar (the DB keeps them all).
