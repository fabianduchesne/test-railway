from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import psycopg2
import os

app = FastAPI()

# Serve static files (logo, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


@app.get("/db-hello")
def db_hello():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"postgres_version": version[0]}
    except Exception as e:
        return {"error": str(e)}
