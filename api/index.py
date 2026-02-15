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
        # Return timestamp (seconds) to avoid timezone parsing issues in JS
        cur.execute("SELECT event_type, created_at FROM sleep_events ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"type": r[0], "timestamp": r[1].replace(tzinfo=timezone.utc).timestamp()} for r in rows]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str, offset_minutes: int = 0):
    try:
        # 1. Calculate the actual time on the server
        now_utc = datetime.now(timezone.utc)
        actual_time = now_utc - timedelta(minutes=int(offset_minutes))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 2. Insert the new event
        cur.execute(
            "INSERT INTO sleep_events (event_type, created_at) VALUES (%s, %s)",
            (event_type, actual_time)
        )
        conn.commit()

        # 3. If waking up, calculate duration immediately on the server
        duration_hours = None
        if event_type == "wake":
            # Find the most recent sleep before this wake time
            cur.execute("""
                SELECT created_at FROM sleep_events 
                WHERE event_type = 'sleep' AND created_at < %s 
                ORDER BY created_at DESC LIMIT 1
            """, (actual_time,))
            last_sleep = cur.fetchone()
            
            if last_sleep:
                sleep_time = last_sleep[0]
                # Ensure timezone awareness for math
                if sleep_time.tzinfo is None:
                    sleep_time = sleep_time.replace(tzinfo=timezone.utc)
                
                # Calculate difference in hours
                diff_seconds = (actual_time - sleep_time).total_seconds()
                duration_hours = diff_seconds / 3600.0

        cur.close()
        conn.close()
        
        return {
            "status": "success", 
            "duration": duration_hours,
            "logged_at": actual_time.timestamp()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}