import sqlite3
import os

# Import the exact same path that our queries use!
from app.config import DB_PATH

def initialize_db():
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Meetings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            notes TEXT,
            audio_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Transcripts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            full_text TEXT,
            FOREIGN KEY(meeting_id) REFERENCES Meetings(id) ON DELETE CASCADE
        )
    ''')

    # Create Summaries Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            short_summary TEXT,
            decisions_made TEXT,
            FOREIGN KEY(meeting_id) REFERENCES Meetings(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {DB_PATH}")

if __name__ == "__main__":
    initialize_db()