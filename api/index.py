import os
import psycopg2
from fastapi import FastAPI
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

@app.get("/api/history")
def get_history():
    """Fetches the last 7 entries to calculate sleep length"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT event_type, created_at FROM sleep_events ORDER BY created_at DESC LIMIT 14")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Transform data for the frontend
        return [{"type": r[0], "time": r[1].isoformat()} for r in rows]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str, offset_minutes: int = 0):
    try:
        # Calculate the actual time (now minus the offset)
        actual_time = datetime.now() - timedelta(minutes=offset_minutes)
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Use the calculated time instead of DB default now()
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