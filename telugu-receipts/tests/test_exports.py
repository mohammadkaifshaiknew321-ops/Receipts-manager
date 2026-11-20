import json
import os
import urllib.request
import zipfile
from io import BytesIO


BASE = os.getenv("RECEIPT_BASE_URL", "http://127.0.0.1:8000")
DATA = {
    "date": "2026-11-20",
    "mandal": "టెస్ట్ మండలం",
    "name": "శ్రీ రవి Kumar",
    "account": "1234567890",
    "ifsc": "SBIN0001234",
    "bank": "SBI తెలుగు Branch",
}


def export(fmt):
    req = urllib.request.Request(
        f"{BASE}/api/export/{fmt}",
        data=json.dumps(DATA, ensure_ascii=False).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return response.status, response.read()


def test_docx_contains_telugu_and_expected_formatting():
    status, content = export("docx")
    assert status == 200
    with zipfile.ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml").decode()
    assert "రశీదు" in xml
    assert "శ్రీ రవి Kumar" in xml
    assert 'w:ascii="Nirmala UI"' in xml


def test_pdf_is_valid_and_contains_embedded_font_data():
    status, content = export("pdf")
    assert status == 200
    assert content.startswith(b"%PDF-")
    assert b"/ToUnicode" in content
    assert len(content) > 10_000
