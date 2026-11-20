# Runtime Validation Report

**Generated**: 2026-11-19
**Target**: `~/Downloads/telugu-receipts`

## Summary

| Step | Status | Exit Code | Details |
|---|---:|---:|---|
| FastAPI startup | PASS | 0 | Uvicorn served `http://127.0.0.1:8000`; `/api/template` returned 200 |
| React frontend | PASS | 0 | Static React page loaded from `/`; browser rendered Telugu UI and preview |
| Backend regression tests | PASS | 0 | `4 passed in 0.26s` |
| Word export | PASS | 0 | Valid OOXML; Telugu, English, alignment, and `Nirmala UI` font settings verified |
| PDF export | PASS | 0 | Valid one-page PDF; Telugu glyphs visibly rendered in browser inspection |
| Browser CRUD/search/delete | PASS | 0 | Created, searched, edited, and deleted receipts through the UI |
| Backup/recovery | PASS | 0 | Backup SQLite database opened successfully and contained both required tables |

**Overall**: PASS after fixing PDF export on macOS.

## Tests Run

- `tests/test_receipts_api.py`
  - Create receipt
  - Search by Telugu mandal
  - Update receipt
  - Delete and verify it is gone
- `tests/test_exports.py`
  - Word output contains Telugu and English sample data
  - Word output contains the configured Telugu-capable font name
  - PDF starts with `%PDF-`, contains Unicode mapping data, and is non-empty
- `tests/test_template_isolation.py`
  - Default template update succeeds without a password
  - Existing receipt data remains unchanged after template update
  - Backup exists and can be opened by SQLite

Command:

```bash
/usr/local/bin/python3 -m pytest -q tests
```

Result:

```text
....                                                                     [100%]
4 passed in 0.26s
```

## Reference Template Inspection

The browser preview was compared with the supplied reference image. The title `రశీదు`, Telugu body text, signature area, and English bank details are present with matching general order and spacing. It is structurally close, but not pixel-identical: the browser preview and generated documents use responsive HTML/PDF layout rather than the exact dimensions of the photographed document.

## Bugs Fixed

1. **PDF export returned HTTP 500 on macOS** because WeasyPrint could not load native Pango/GLib libraries.
   - Added an `fpdf2` fallback using HarfBuzz and the macOS Kohinoor Telugu font.
   - Added TTC-to-TTF extraction so Chrome/macOS displays the embedded Telugu glyphs correctly.
   - Added safe character wrapping and one-page layout handling.
2. Added the fallback dependencies to `backend/requirements.txt`.

## Remaining Limitations

- WeasyPrint still requires native Pango/GLib libraries for its preferred path. On this Mac, the tested fallback is used automatically.
- Word rendering was validated by inspecting the generated OOXML, Unicode text, font settings, paragraph alignment, and spacing metadata. Microsoft Word itself was not installed in the test environment.
- The frontend is a static React page served by FastAPI; there is no separate `package.json` React development/build project.
- Docker was unavailable, so no containerized infrastructure test was applicable. The application uses local SQLite.
- Saving the default template is unauthenticated. Keep the service bound to localhost and do not expose it to untrusted networks.

## Run Locally on a MacBook Air M2

From the project directory:

```bash
cd ~/Downloads/telugu-receipts
/usr/local/bin/python3 -m pip install -r backend/requirements.txt
```

Start the application:

```bash
cd backend
/usr/local/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Run the regression tests in another terminal while the server is running:

```bash
cd ~/Downloads/telugu-receipts
/usr/local/bin/python3 -m pytest -q tests
```

The SQLite database is `backend/receipts.db`; automatic backups are stored in `backend/backups/`.
