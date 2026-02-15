import os
import psycopg2
from fastapi import FastAPI
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables for database connection
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

@app.get("/api/state")
def get_last_state():
    """Returns the most recent event type to determine if the UI should be Day or Night mode."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Fetch the very last event logged to set the current UI state 
        cur.execute("SELECT event_type FROM sleep_events ORDER BY created_at DESC LIMIT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"last_event": result[0] if result else "wake"}
    except Exception:
        # Default to 'wake' (Night mode) if no data or connection error 
        return {"last_event": "wake"}

@app.get("/api/history")
def get_history():
    """Returns the last 50 logs so the frontend can calculate sleep durations and display history."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Fetch 50 records to ensure we have enough data for a robust history list
        cur.execute("SELECT event_type, created_at FROM sleep_events ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Return as ISO format strings for easy parsing by JavaScript Date objects 
        return [{"type": r[0], "time": r[1].isoformat()} for r in rows]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str, offset_minutes: int = 0):
    """
    Logs a sleep or wake event. 
    Applies the 'Forgot?' offset by subtracting minutes from the current UTC time.
    """
    try:
        # Get current time in UTC
        now_utc = datetime.now(timezone.utc)
        
        # Apply the retrospective offset (e.g., if you forgot to log 120 mins ago) 
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