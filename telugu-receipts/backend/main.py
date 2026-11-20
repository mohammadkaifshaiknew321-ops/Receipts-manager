import io, json, os, shutil, sqlite3, datetime, html, textwrap, tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

BASE = Path(__file__).parent
DB = os.getenv("RECEIPT_DB", str(BASE / "receipts.db"))
FIELDS = ["date", "mandal", "name", "account", "ifsc", "bank"]
BLANK = {"date": "_" * 16, "mandal": "_" * 26}
WORD_FONT = "Nirmala UI"  # ships with Windows Word; has Telugu

# Original template, transcribed from the reference image. s = style.
DEFAULT = [
    {"s": "space", "t": ""}, {"s": "space", "t": ""},
    {"s": "title", "t": "రశీదు"},
    {"s": "space", "t": ""},
    {"s": "body", "t": "తేదీ {{date}} న గరివిడి"},
    {"s": "justify", "t": "మండలం {{mandal}} గ్రామం లో పొలంబడి కార్యక్రమం ఏర్పాటు చేసిన స్థలమును శుభ్రపరుచుటకు రూ.500/- ( అక్షరములా అయిదు వందల రూపాయలు మాత్రమే మా RBK ఇన్ఛార్జి VAA/VHA/AEO/MPEO/BTM వారి నుండి నాకు ముట్టినవి"},
    {"s": "space", "t": ""}, {"s": "space", "t": ""}, {"s": "space", "t": ""},
    {"s": "sig", "t": "సంతకం"},
    {"s": "space", "t": ""}, {"s": "space", "t": ""}, {"s": "space", "t": ""},
    {"s": "label", "t": "Name of the VAA/VHA/MPEO/AEO/BTM : {{name}}"},
    {"s": "label", "t": "BANK A/C No    : {{account}}"},
    {"s": "label", "t": "IFSC code        : {{ifsc}}"},
    {"s": "label", "t": "Bank Name & Branch : {{bank}}"},
]

def con():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    with con() as c:
        c.execute("create table if not exists receipts(id integer primary key, data text, created text, updated text)")
        c.execute("create table if not exists template(id integer primary key, body text, saved text)")
        if not c.execute("select 1 from template").fetchone():
            c.execute("insert into template(body,saved) values(?,?)", (json.dumps(DEFAULT), now()))
    backup()

def now(): return datetime.datetime.now().isoformat(timespec="seconds")

def backup():
    if Path(DB).exists():
        d = Path(DB).parent / "backups"; d.mkdir(exist_ok=True)
        shutil.copy(DB, d / f"receipts-{datetime.date.today()}.db")

def get_template():
    with con() as c:
        return json.loads(c.execute("select body from template order by id desc limit 1").fetchone()[0])

class Data(BaseModel):
    date: str = Field("", max_length=60); mandal: str = Field("", max_length=120)
    name: str = Field("", max_length=150); account: str = Field("", max_length=40)
    ifsc: str = Field("", max_length=20); bank: str = Field("", max_length=200)

class Line(BaseModel):
    s: str = Field(pattern="^(title|body|justify|sig|label|space)$")
    t: str = Field(max_length=2000)

def fill(t, d):
    for k in FIELDS:
        t = t.replace("{{%s}}" % k, (d.get(k) or "").strip() or BLANK.get(k, ""))
    return t

app = FastAPI(title="Telugu Receipt Manager")
init()

@app.get("/api/template")
def tpl(): return get_template()

@app.put("/api/template")
def save_tpl(lines: list[Line]):
    backup()
    with con() as c:  # append-only: old templates kept as history, records untouched
        c.execute("insert into template(body,saved) values(?,?)", (json.dumps([l.model_dump() for l in lines]), now()))
    return {"ok": True}

def row(r): return {"id": r["id"], "created": r["created"], "updated": r["updated"], **json.loads(r["data"])}

@app.get("/api/receipts")
def list_(q: str = ""):
    with con() as c:
        rows = [row(r) for r in c.execute("select * from receipts order by id desc")]
    q = q.lower().strip()
    return [r for r in rows if not q or q in " ".join(str(v) for v in r.values()).lower()]

@app.post("/api/receipts")
def create(d: Data):
    with con() as c:
        i = c.execute("insert into receipts(data,created,updated) values(?,?,?)", (d.model_dump_json(), now(), now())).lastrowid
    return {"id": i}

@app.put("/api/receipts/{i}")
def update(i: int, d: Data):
    with con() as c:
        if not c.execute("update receipts set data=?, updated=? where id=?", (d.model_dump_json(), now(), i)).rowcount:
            raise HTTPException(404, "Receipt not found")
    return {"ok": True}

@app.delete("/api/receipts/{i}")
def delete(i: int):
    with con() as c: c.execute("delete from receipts where id=?", (i,))
    return {"ok": True}

def make_docx(d):
    doc = Document()
    sec = doc.sections[0]
    for p in ("left_margin", "right_margin"): setattr(sec, p, Pt(60))
    for l in get_template():
        p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.8
        text = fill(l["t"], d)
        if l["s"] == "justify": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if l["s"] == "title": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if not text: continue
        r = p.add_run(text)
        r.font.size = Pt(26 if l["s"] == "title" else 14)
        r.bold = l["s"] in ("title", "sig", "label"); r.underline = l["s"] == "title"
        rf = r._element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:ascii", "w:hAnsi", "w:cs"): rf.set(qn(a), WORD_FONT)
        rpr = r._element.rPr
        for tag in ("w:szCs", "w:bCs"):
            el = rpr.makeelement(qn(tag), {qn("w:val"): "52" if l["s"] == "title" else "28"} if tag == "w:szCs" else {})
            rpr.append(el)
    b = io.BytesIO(); doc.save(b); return b.getvalue()

def make_pdf(d):
    css = """@page{size:A4;margin:25mm 20mm}body{font-family:'Noto Sans Telugu','Noto Sans',sans-serif;font-size:14pt}
    p{margin:0;line-height:2;min-height:1em}.title{text-align:center;font-size:28pt;font-weight:bold;text-decoration:underline}
    .justify{text-align:justify}.sig,.label{font-weight:bold}"""
    body = "".join(f'<p class="{l["s"]}">{html.escape(fill(l["t"], d)) or "&nbsp;"}</p>' for l in get_template())
    try:
        from weasyprint import HTML  # needs Pango + fonts-noto-core (Noto Sans Telugu)
        return HTML(string=f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>").write_pdf()
    except (ImportError, OSError):
        # WeasyPrint's native Pango libraries are not present on a minimal macOS
        # install. fpdf2 uses HarfBuzz and embeds the system Telugu font instead.
        from fpdf import FPDF

        font = next((p for p in (
            "/System/Library/Fonts/KohinoorTelugu.ttc",
            "/Library/Fonts/NotoSansTelugu-Regular.ttf",
        ) if Path(p).exists()), None)
        if not font:
            raise RuntimeError("No Telugu-capable font found for PDF export")

        extracted_font = None
        if font.endswith(".ttc"):
            from fontTools.ttLib import TTCollection
            extracted_font = tempfile.NamedTemporaryFile(suffix=".ttf", delete=False)
            extracted_font.close()
            TTCollection(font).fonts[2].save(extracted_font.name)
            font = extracted_font.name
        try:
            pdf = FPDF(format="A4")
            pdf.set_margins(20, 25, 20)
            pdf.set_auto_page_break(True, 25)
            pdf.add_page()
            pdf.add_font("Telugu", fname=font)
            for line in get_template():
                style = line["s"]
                text = fill(line["t"], d) or " "
                size = 28 if style == "title" else 14
                pdf.set_font("Telugu", size=size)
                align = "C" if style == "title" else "L"
                chunks = textwrap.wrap(text, width=24 if style == "title" else 58,
                                       break_long_words=True, break_on_hyphens=False) or [" "]
                for chunk in chunks:
                    pdf.cell(pdf.epw, size * 0.75, chunk, align=align)
                    pdf.ln(size * 0.75)
                if style == "title":
                    y = pdf.get_y()
                    pdf.line(pdf.l_margin, y - 2, pdf.l_margin + pdf.epw, y - 2)
            return bytes(pdf.output())
        finally:
            if extracted_font:
                Path(extracted_font.name).unlink(missing_ok=True)

@app.post("/api/export/{fmt}")
def export(fmt: str, d: Data):
    data = d.model_dump()
    if fmt == "docx":
        return Response(make_docx(data), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": "attachment; filename=receipt.docx"})
    if fmt == "pdf":
        return Response(make_pdf(data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=receipt.pdf"})
    raise HTTPException(404, "Unknown format")

app.mount("/", StaticFiles(directory=BASE.parent / "frontend", html=True))
