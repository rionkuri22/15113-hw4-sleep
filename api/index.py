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
        # Fetch 100 rows to ensure we catch recent sessions
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
        # Calculate the intended timestamp
        actual_time = now_utc - timedelta(minutes=int(offset_minutes))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Fetch the very last log of the same type
        cur.execute("""
            SELECT id, created_at FROM sleep_events 
            WHERE event_type = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (event_type,))
        last_entry = cur.fetchone()

        should_update = False
        if last_entry:
            last_id, last_time = last_entry
            
            # CRITICAL FIX: Compare the new actual_time with the DB last_time.
            # If they are within 5 minutes of each other, it's a duplicate/correction.
            # Previously this failed because it compared 'now' vs 'offset time'.
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
                
            time_diff = abs((actual_time - last_time).total_seconds())
            
            if time_diff < 300: # 5 minutes
                should_update = True
                target_id = last_id

        if should_update:
            cur.execute("UPDATE sleep_events SET created_at = %s WHERE id = %s", (actual_time, target_id))
        else:
            cur.execute("INSERT INTO sleep_events (event_type, created_at) VALUES (%s, %s)", (event_type, actual_time))
        
        conn.commit()

        # 2. Calculate duration if waking up
        duration_hours = None
        if event_type == "wake":
            cur.execute("""
                SELECT created_at FROM sleep_events 
                WHERE event_type = 'sleep' AND created_at < %s 
                ORDER BY created_at DESC LIMIT 1
            """, (actual_time,))
            last_sleep = cur.fetchone()
            
            if last_sleep:
                sleep_time = last_sleep[0]
                if sleep_time.tzinfo is None:
                    sleep_time = sleep_time.replace(tzinfo=timezone.utc)
                diff_seconds = (actual_time - sleep_time).total_seconds()
                duration_hours = diff_seconds / 3600.0

        cur.close()
        conn.close()
        
        return {"status": "success", "duration": duration_hours}
    except Exception as e:
        return {"status": "error", "message": str(e)}