from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


@app.get("/")
def read_root():
    return {"Hello": "World"}


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

@app.get("/debug-env")
def debug_env():
    return dict(os.environ)

