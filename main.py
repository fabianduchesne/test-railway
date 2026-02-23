from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
import psycopg2
import resend
import os
from datetime import datetime, timezone

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

resend.api_key = os.environ["RESEND_API_KEY"]
RECIPIENT_EMAIL = os.environ["CONTACT_RECIPIENT_EMAIL"]  # where submissions are sent to


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def ensure_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id        SERIAL PRIMARY KEY,
            name      TEXT NOT NULL,
            email     TEXT NOT NULL,
            comment   TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def startup():
    ensure_table()


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/db-hello")
def db_hello():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        return {"postgres_version": version[0]}
    except Exception as e:
        return {"error": str(e)}


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    comment: str


@app.post("/contact")
def contact(form: ContactForm):
    try:
        # 1. Save to DB
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO contact_submissions (name, email, comment) VALUES (%s, %s, %s) RETURNING id, created_at",
            (form.name, form.email, form.comment),
        )
        row = cur.fetchone()
        submission_id = row[0]
        created_at = row[1]
        conn.commit()
        cur.close()
        conn.close()

        # 2. Send email via Resend
        resend.Emails.send({
            "from": "NoName Factory <onboarding@resend.dev>",  # replace with your verified domain later
            "to": [RECIPIENT_EMAIL],
            "subject": f"New contact from {form.name}",
            "html": f"""
                <h2>New Contact Submission</h2>
                <p><strong>Name:</strong> {form.name}</p>
                <p><strong>Email:</strong> {form.email}</p>
                <p><strong>Message:</strong></p>
                <blockquote>{form.comment}</blockquote>
                <hr/>
                <small>Submission #{submission_id} — {created_at.isoformat()}</small>
            """,
        })

        return {
            "success": True,
            "submission_id": submission_id,
            "email_sent_to": RECIPIENT_EMAIL,
            "timestamp": created_at.isoformat(),
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
