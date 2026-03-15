import sqlite3
from app.config import DB_PATH

def create_meeting(title, date, start_time, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Meetings (title, date, start_time, notes)
        VALUES (?, ?, ?, ?)
    ''', (title, date, start_time, notes))
    conn.commit()
    conn.close()

def get_all_meetings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, date, start_time, notes, audio_path 
        FROM Meetings 
        ORDER BY date ASC, start_time ASC
    ''')
    meetings = cursor.fetchall()
    conn.close()
    return [dict(row) for row in meetings]

def update_meeting_audio(meeting_id, audio_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE Meetings SET audio_path = ? WHERE id = ?
    ''', (audio_path, meeting_id))
    conn.commit()
    conn.close()

def delete_meeting(meeting_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM Meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()

def save_ai_results(meeting_id, transcript, summary, decisions):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Transcripts (meeting_id, full_text) VALUES (?, ?)", (meeting_id, transcript))
    cursor.execute("INSERT INTO Summaries (meeting_id, short_summary, decisions_made) VALUES (?, ?, ?)", (meeting_id, summary, decisions))
    conn.commit()
    conn.close()

def get_meeting_details(meeting_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT full_text FROM Transcripts WHERE meeting_id = ?", (meeting_id,))
    t_row = cursor.fetchone()
    
    cursor.execute("SELECT short_summary, decisions_made FROM Summaries WHERE meeting_id = ?", (meeting_id,))
    s_row = cursor.fetchone()
    
    conn.close()
    
    return {
        "transcript": t_row['full_text'] if t_row else "No transcript available.",
        "summary": s_row['short_summary'] if s_row else "No summary available.",
        "decisions": s_row['decisions_made'] if s_row else "No action items available."
    }

def update_meeting(meeting_id, title, date, start_time, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE Meetings 
        SET title = ?, date = ?, start_time = ?, notes = ? 
        WHERE id = ?
    ''', (title, date, start_time, notes, meeting_id))
    conn.commit()
    conn.close()

def clear_meeting_audio_and_ai(meeting_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE Meetings SET audio_path = NULL WHERE id = ?", (meeting_id,))
    cursor.execute("DELETE FROM Transcripts WHERE meeting_id = ?", (meeting_id,))
    cursor.execute("DELETE FROM Summaries WHERE meeting_id = ?", (meeting_id,))
    conn.commit()
    conn.close()

# --- BRAND NEW SEARCH QUERY ---
def search_meetings(search_term):
    """Searches for meetings by title or notes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Adding % allows SQL to search for partial matches (e.g., searching "mark" finds "Marketing")
    query = f"%{search_term}%"
    
    cursor.execute('''
        SELECT id, title, date, start_time, notes, audio_path 
        FROM Meetings 
        WHERE title LIKE ? OR notes LIKE ?
        ORDER BY date DESC
    ''', (query, query))
    
    meetings = cursor.fetchall()
    conn.close()
    return [dict(row) for row in meetings]