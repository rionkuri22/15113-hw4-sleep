import os
import psycopg2
from fastapi import FastAPI
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

@app.get("/api/state")
def get_last_state():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT event_type FROM sleep_events ORDER BY created_at DESC LIMIT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"last_event": result[0] if result else "wake"}
    except Exception:
        return {"last_event": "wake"}

@app.get("/api/history")
def get_history():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT event_type, created_at FROM sleep_events ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Change: Send a Unix timestamp (seconds) to avoid ISO parsing bugs
        return [{"type": r[0], "timestamp": r[1].replace(tzinfo=timezone.utc).timestamp()} for r in rows]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str, offset_minutes: int = 0):
    try:
        now_utc = datetime.now(timezone.utc)
        actual_time = now_utc - timedelta(minutes=int(offset_minutes))
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sleep_events (event_type, created_at) VALUES (%s, %s)",
            (event_type, actual_time)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}