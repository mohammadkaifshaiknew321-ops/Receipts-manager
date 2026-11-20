# Telugu Receipt Manager
## Setup
    sudo apt install fonts-noto-core libpango-1.0-0 libpangoft2-1.0-0   # Telugu font + shaping for PDF
    cd backend && pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload
Open http://localhost:8000
- Receipts store only field values; the template is stored separately (append-only history), so editing it never alters records.
- Saving the default template does not require a password. Keep the app bound to localhost; do not expose it to untrusted networks.
- DB is copied to backend/backups/ at startup and before each template change.
- Word output uses the "Nirmala UI" font (built into Windows); on other systems Word substitutes a Telugu font.
