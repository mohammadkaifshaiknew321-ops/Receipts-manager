import json
import os
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path


BASE = os.getenv("RECEIPT_BASE_URL", "http://127.0.0.1:8000")
DB = Path(os.getenv("RECEIPT_DB", str(Path(__file__).parents[1] / "backend" / "receipts.db")))


def request(path, method="GET", payload=None, headers=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read())


def test_template_edit_does_not_change_saved_receipt_and_backup_exists():
    _, original = request("/api/template")
    data = {
        "date": "2026-11-21",
        "mandal": "Isolation Mandal",
        "name": "Isolation User",
        "account": "222",
        "ifsc": "IFSC2",
        "bank": "Isolation Bank",
    }
    _, created = request("/api/receipts", "POST", data)
    receipt_id = created["id"]
    changed = [*original, {"s": "body", "t": "Temporary template line"}]
    try:
        assert request("/api/template", "PUT", changed)[0] == 200
        _, rows = request("/api/receipts")
        assert next(row for row in rows if row["id"] == receipt_id)["name"] == "Isolation User"
        backups = list((DB.parent / "backups").glob("receipts-*.db"))
        assert backups
        with tempfile.TemporaryDirectory() as directory:
            restored_db = Path(directory) / "restored.db"
            shutil.copy2(max(backups, key=lambda path: path.stat().st_mtime), restored_db)
            with sqlite3.connect(restored_db) as connection:
                restored = connection.execute(
                    "select data from receipts where id=?", (receipt_id,)
                ).fetchone()
                assert restored and json.loads(restored[0])["name"] == "Isolation User"
                assert connection.execute("select count(*) from template").fetchone()[0] > 0
        with sqlite3.connect(DB) as connection:
            assert connection.execute("select count(*) from receipts where id=?", (receipt_id,)).fetchone()[0] == 1
    finally:
        request("/api/template", "PUT", original)
        request(f"/api/receipts/{receipt_id}", "DELETE")
