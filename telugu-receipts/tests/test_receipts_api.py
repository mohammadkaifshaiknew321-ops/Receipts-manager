import json
import os
import urllib.parse
import urllib.request


BASE = os.getenv("RECEIPT_BASE_URL", "http://127.0.0.1:8000")


def request(path, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read())


def test_create_search_update_delete_receipt():
    data = {
        "date": "2026-11-20",
        "mandal": "టెస్ట్ మండలం",
        "name": "Test User",
        "account": "111",
        "ifsc": "IFSC1",
        "bank": "Test Bank",
    }
    _, created = request("/api/receipts", "POST", data)
    receipt_id = created["id"]
    try:
        _, rows = request("/api/receipts?q=" + urllib.parse.quote("టెస్ట్ మండలం"))
        assert any(row["id"] == receipt_id and row["name"] == "Test User" for row in rows)

        updated = {**data, "name": "Edited User"}
        assert request(f"/api/receipts/{receipt_id}", "PUT", updated)[0] == 200
        _, rows = request("/api/receipts")
        assert next(row for row in rows if row["id"] == receipt_id)["name"] == "Edited User"
    finally:
        assert request(f"/api/receipts/{receipt_id}", "DELETE")[0] == 200
        _, rows = request("/api/receipts")
        assert not any(row["id"] == receipt_id for row in rows)
