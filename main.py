from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import psycopg2
import resend
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:4200").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

resend.api_key = os.environ["RESEND_API_KEY"]
RECIPIENT_EMAIL = os.environ["CONTACT_RECIPIENT_EMAIL"]


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def ensure_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id         SERIAL PRIMARY KEY,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            comment    TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def startup():
    ensure_table()


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

        resend.Emails.send({
            "from": "NoName Factory <onboarding@resend.dev>",
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
