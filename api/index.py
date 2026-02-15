import os
import psycopg2
from fastapi import FastAPI
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/api/state")
def get_last_state():
    try:
        conn = get_db_connection()
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
        conn = get_db_connection()
        cur = conn.cursor()
        # Return 100 rows to ensure we catch the start of current sessions
        cur.execute("SELECT id, event_type, created_at FROM sleep_events ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "type": r[1], "timestamp": r[2].replace(tzinfo=timezone.utc).timestamp()} for r in rows]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str, offset_minutes: int = 0):
    try:
        now_utc = datetime.now(timezone.utc)
        actual_time = now_utc - timedelta(minutes=int(offset_minutes))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check for duplicate events within 5 minutes to prevent double-clicks
        cur.execute("""
            SELECT id, created_at FROM sleep_events 
            WHERE event_type = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (event_type,))
        last_entry = cur.fetchone()

        should_update = False
        if last_entry:
            last_id, last_time = last_entry
            if (now_utc - last_time).total_seconds() < 300:
                should_update = True
                target_id = last_id

        if should_update:
            cur.execute("UPDATE sleep_events SET created_at = %s WHERE id = %s", (actual_time, target_id))
        else:
            cur.execute("INSERT INTO sleep_events (event_type, created_at) VALUES (%s, %s)", (event_type, actual_time))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}