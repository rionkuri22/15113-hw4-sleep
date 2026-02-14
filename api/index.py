import os
import psycopg2
from fastapi import FastAPI
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

@app.get("/api/state")
def get_last_state():
    """Returns the last logged event so the UI can set the theme"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Get the most recent event type
        cur.execute("SELECT event_type FROM sleep_events ORDER BY created_at DESC LIMIT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        # Default to 'wake' (day theme) if the DB is empty
        return {"last_event": result[0] if result else "wake"}
    except Exception as e:
        return {"last_event": "wake", "error": str(e)}

@app.post("/api/log")
async def log_event(event_type: str):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO sleep_events (event_type) VALUES (%s)", (event_type,))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "event": event_type}
    except Exception as e:
        return {"status": "error", "message": str(e)}