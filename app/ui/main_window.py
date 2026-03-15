import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QStackedWidget, QLineEdit, 
                               QTextEdit, QDateEdit, QTimeEdit, QFrame, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt, QDate, QTime, QTimer, QThread, Signal, QPoint

from app.database.queries import (create_meeting, get_all_meetings, update_meeting_audio, 
                                  delete_meeting, save_ai_results, get_meeting_details, 
                                  update_meeting, clear_meeting_audio_and_ai, search_meetings)
from app.audio.recorder import AudioRecorder
from app.config import RECORDINGS_DIR
from app.ai.transcriber import transcribe_audio
from app.ai.summarizer import generate_meeting_summary

# --- Complete Stylesheet for Custom UI ---
STYLESHEET = """
QMainWindow { 
    background-color: transparent; 
}
#MainContainer { 
    background-color: #F5F5F6; 
    border-radius: 15px; 
}
#TitleBar {
    background-color: #2D2D30;
    border-top-left-radius: 15px;
    border-top-right-radius: 15px;
    min-height: 45px;
}
#TitleLabel {
    color: #FFFFFF;
    font-weight: bold;
    font-size: 14px;
    margin-left: 15px;
}
#WindowButtons {
    color: white;
    background: transparent;
    border: none;
    font-size: 16px;
    padding: 10px 18px;
}
#WindowButtons:hover {
    background-color: #444444;
}
#CloseButton:hover {
    background-color: #E81123;
    border-top-right-radius: 15px;
}
QFrame#Sidebar { 
    background-color: #3F51B5; 
    border-bottom-left-radius: 15px;
}
QPushButton.NavButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; text-align: left; padding: 12px; border: none; }
QPushButton.NavButton:hover { background-color: #7E57C2; border-radius: 6px; }
QPushButton.PrimaryAction { background-color: #3F51B5; color: white; font-size: 14px; font-weight: bold; padding: 10px; border-radius: 6px; }
QPushButton.PrimaryAction:hover { background-color: #7E57C2; }
QPushButton.RecordButton { background-color: #E53935; color: white; font-weight: bold; padding: 8px 15px; border-radius: 6px; }
QPushButton.RecordButton:hover { background-color: #EF5350; }
QPushButton.ViewButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 15px; border-radius: 6px; }
QPushButton.ViewButton:hover { background-color: #66BB6A; }
QPushButton.DeleteButton { background-color: transparent; color: #757575; font-weight: bold; padding: 8px; border: 1px solid #BDBDBD; border-radius: 6px; }
QPushButton.DeleteButton:hover { background-color: #EEEEEE; color: #D32F2F; border-color: #D32F2F; }
QPushButton.EditButton { background-color: transparent; color: #3F51B5; font-weight: bold; padding: 8px; border: 1px solid #3F51B5; border-radius: 6px; }
QPushButton.EditButton:hover { background-color: #E8EAF6; }
QLabel.Header { font-size: 24px; font-weight: bold; color: #333333; padding-bottom: 10px; }
QLabel.CategoryHeader { font-size: 18px; font-weight: bold; color: #3F51B5; margin-top: 15px; padding-bottom: 5px; }
QLabel.CategoryHeaderFinished { font-size: 18px; font-weight: bold; color: #4CAF50; margin-top: 25px; padding-bottom: 5px; }
QLabel.Timer { font-size: 64px; font-weight: bold; color: #E53935; }
QLineEdit, QTextEdit, QDateEdit, QTimeEdit { border: 1px solid #CCCCCC; border-radius: 4px; padding: 8px; background-color: white; }
QFrame.MeetingCard { background-color: white; border-radius: 8px; border: 1px solid #E0E0E0; margin-bottom: 5px; }
QScrollArea { border: none; background-color: transparent; }
"""

class AIWorker(QThread):
    finished_data = Signal(int, str, str, str) 
    error = Signal(str)
    def __init__(self, meeting_id, audio_path):
        super().__init__()
        self.meeting_id = meeting_id; self.audio_path = audio_path
    def run(self):
        try:
            transcript = transcribe_audio(self.audio_path)
            summary_data = generate_meeting_summary(transcript)
            summary = summary_data.get('short_summary', '')
            if isinstance(summary, list): summary = " ".join(str(item) for item in summary)
            decisions = summary_data.get('decisions', '')
            if isinstance(decisions, list): decisions = "\n".join(f"• {str(item)}" for item in decisions)
            self.finished_data.emit(self.meeting_id, str(transcript), str(summary), str(decisions))
        except Exception as e:
            self.error.emit(str(e))

class DetailsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; layout = QVBoxLayout(self)
        self.header = QLabel("Meeting Details"); self.header.setProperty("class", "Header"); layout.addWidget(self.header)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        for lbl_text, attr_name in [("Summary", "summary_text"), ("Action Items & Decisions", "decisions_text"), ("Full Transcript", "transcript_text")]:
            lbl = QLabel(lbl_text); lbl.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;"); self.content_layout.addWidget(lbl)
            txt = QTextEdit(); txt.setReadOnly(True); setattr(self, attr_name, txt); self.content_layout.addWidget(txt)
        scroll.setWidget(content_widget); layout.addWidget(scroll)

    def load_details(self, meeting_id, title):
        self.header.setText(f"Details: {title}")
        data = get_meeting_details(meeting_id)
        self.summary_text.setText(data['summary']); self.decisions_text.setText(data['decisions']); self.transcript_text.setText(data['transcript'])

class RecordingPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.current_meeting_id = None; self.recorder = None; self.seconds_elapsed = 0
        layout = QVBoxLayout(self); layout.setAlignment(Qt.AlignCenter)
        self.title_label = QLabel("Meeting Title"); self.title_label.setProperty("class", "Header"); layout.addWidget(self.title_label)
        self.timer_label = QLabel("00:00"); self.timer_label.setProperty("class", "Timer"); layout.addWidget(self.timer_label)
        self.status_label = QLabel(""); layout.addWidget(self.status_label)
        self.stop_btn = QPushButton("Stop Recording"); self.stop_btn.setProperty("class", "PrimaryAction")
        self.stop_btn.clicked.connect(self.stop_recording); layout.addWidget(self.stop_btn)
        self.timer = QTimer(); self.timer.timeout.connect(self.update_timer)

    def start_recording(self, meeting_id, meeting_title):
        self.current_meeting_id = meeting_id; self.title_label.setText(f"Recording: {meeting_title}")
        self.seconds_elapsed = 0; self.timer_label.setText("00:00"); self.stop_btn.setEnabled(True)
        filename = os.path.join(RECORDINGS_DIR, f"meeting_{meeting_id}.wav")
        self.recorder = AudioRecorder(filename); self.recorder.start(); self.timer.start(1000)

    def update_timer(self):
        self.seconds_elapsed += 1
        mins, secs = divmod(self.seconds_elapsed, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def stop_recording(self):
        self.timer.stop(); self.stop_btn.setEnabled(False); self.status_label.setText("AI is processing...")
        if self.recorder:
            filepath = self.recorder.stop()
            update_meeting_audio(self.current_meeting_id, filepath)
            self.ai_worker = AIWorker(self.current_meeting_id, filepath)
            self.ai_worker.finished_data.connect(self.on_ai_finished); self.ai_worker.start()

    def on_ai_finished(self, meeting_id, transcript, summary, decisions):
        save_ai_results(meeting_id, transcript, summary, decisions)
        self.status_label.setText(""); self.main_window.page_home.refresh_meetings()
        self.main_window.content_area.setCurrentWidget(self.main_window.page_home)

class HomePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.main_layout = QVBoxLayout(self) 
        header = QLabel("Dashboard"); header.setProperty("class", "Header"); self.main_layout.addWidget(header)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        
        up_header = QLabel("Upcoming Meetings"); up_header.setProperty("class", "CategoryHeader"); self.content_layout.addWidget(up_header)
        self.upcoming_container = QVBoxLayout(); self.content_layout.addLayout(self.upcoming_container)
        
        fin_header = QLabel("Finished Meetings"); fin_header.setProperty("class", "CategoryHeaderFinished"); self.content_layout.addWidget(fin_header)
        self.finished_container = QVBoxLayout(); self.content_layout.addLayout(self.finished_container)
        
        self.content_layout.addStretch(); scroll.setWidget(content_widget); self.main_layout.addWidget(scroll)

    def refresh_meetings(self):
        for container in [self.upcoming_container, self.finished_container]:
            while container.count():
                item = container.takeAt(0)
                if item.widget(): item.widget().deleteLater()
        meetings = get_all_meetings()
        for meeting in meetings:
            card = self.main_window.create_meeting_card(meeting)
            if meeting['audio_path']: self.finished_container.addWidget(card)
            else: self.upcoming_container.addWidget(card)

class CreateMeetingPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self); header = QLabel("New Meeting"); header.setProperty("class", "Header"); layout.addWidget(header)
        self.title_input = QLineEdit(); self.title_input.setPlaceholderText("Title"); layout.addWidget(self.title_input)
        self.date_input = QDateEdit(); self.date_input.setDate(QDate.currentDate()); layout.addWidget(self.date_input)
        self.time_input = QTimeEdit(); self.time_input.setTime(QTime.currentTime()); layout.addWidget(self.time_input)
        self.notes_input = QTextEdit(); self.notes_input.setPlaceholderText("Notes"); layout.addWidget(self.notes_input)
        self.save_btn = QPushButton("Save"); self.save_btn.setProperty("class", "PrimaryAction"); layout.addWidget(self.save_btn)
        layout.addStretch()

class EditMeetingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_meeting_id = None; layout = QVBoxLayout(self)
        header = QLabel("Edit Meeting"); header.setProperty("class", "Header"); layout.addWidget(header)
        self.title_input = QLineEdit(); layout.addWidget(self.title_input)
        self.date_input = QDateEdit(); layout.addWidget(self.date_input)
        self.time_input = QTimeEdit(); layout.addWidget(self.time_input)
        self.notes_input = QTextEdit(); layout.addWidget(self.notes_input)
        self.save_btn = QPushButton("Update"); self.save_btn.setProperty("class", "PrimaryAction"); layout.addWidget(self.save_btn)
        layout.addStretch()

    def load_meeting(self, meeting):
        self.current_meeting_id = meeting['id']; self.title_input.setText(meeting['title'])
        self.notes_input.setText(meeting.get('notes', ''))
        d = meeting['date'].split('-'); self.date_input.setDate(QDate(int(d[0]), int(d[1]), int(d[2])))
        t = meeting['start_time'].split(':'); self.time_input.setTime(QTime(int(t[0]), int(t[1])))

class SearchPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; layout = QVBoxLayout(self)
        header = QLabel("Search"); header.setProperty("class", "Header"); layout.addWidget(header)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search..."); layout.addWidget(self.search_bar)
        self.search_bar.textChanged.connect(self.perform_search)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content_widget = QWidget()
        self.results_container = QVBoxLayout(content_widget); self.results_container.setAlignment(Qt.AlignTop)
        scroll.setWidget(content_widget); layout.addWidget(scroll)

    def perform_search(self):
        while self.results_container.count():
            item = self.results_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        results = search_meetings(self.search_bar.text().strip())
        for m in results: self.results_container.addWidget(self.main_window.create_meeting_card(m))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1000, 700); self.setStyleSheet(STYLESHEET)
        
        self.main_container = QFrame(); self.main_container.setObjectName("MainContainer")
        self.setCentralWidget(self.main_container); outer_layout = QVBoxLayout(self.main_container)
        outer_layout.setContentsMargins(0, 0, 0, 0); outer_layout.setSpacing(0)

        # Title Bar
        self.title_bar = QFrame(); self.title_bar.setObjectName("TitleBar")
        title_layout = QHBoxLayout(self.title_bar)
        title_label = QLabel(" AI Meeting Assistant"); title_label.setObjectName("TitleLabel")
        self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("CloseButton"); self.btn_close.setProperty("id", "WindowButtons")
        self.btn_min = QPushButton("—"); self.btn_min.setObjectName("WindowButtons"); self.btn_min.setProperty("id", "WindowButtons")
        title_layout.addWidget(title_label); title_layout.addStretch(); title_layout.addWidget(self.btn_min); title_layout.addWidget(self.btn_close)
        outer_layout.addWidget(self.title_bar)

        # Body
        body = QWidget(); body_layout = QHBoxLayout(body); body_layout.setContentsMargins(0, 0, 0, 0); body_layout.setSpacing(0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(200); sidebar_layout = QVBoxLayout(self.sidebar)
        self.btn_home = QPushButton("🏠 Home"); self.btn_new = QPushButton("➕ New"); self.btn_search = QPushButton("🔍 Search")
        for b in [self.btn_home, self.btn_new, self.btn_search]: b.setProperty("class", "NavButton"); sidebar_layout.addWidget(b)
        sidebar_layout.addStretch(); body_layout.addWidget(self.sidebar)
        
        self.content_area = QStackedWidget()
        self.page_home = HomePage(self); self.page_new = CreateMeetingPage(); self.page_edit = EditMeetingPage() 
        self.page_search = SearchPage(self); self.page_record = RecordingPage(self); self.page_details = DetailsPage(self)
        for p in [self.page_home, self.page_new, self.page_edit, self.page_search, self.page_record, self.page_details]: self.content_area.addWidget(p)
        body_layout.addWidget(self.content_area); outer_layout.addWidget(body)

        # Actions
        self.btn_home.clicked.connect(lambda: self.content_area.setCurrentWidget(self.page_home))
        self.btn_new.clicked.connect(lambda: self.content_area.setCurrentWidget(self.page_new))
        self.btn_search.clicked.connect(lambda: self.content_area.setCurrentWidget(self.page_search))
        self.btn_close.clicked.connect(self.close); self.btn_min.clicked.connect(self.showMinimized)
        self.page_new.save_btn.clicked.connect(self.handle_save_meeting); self.page_edit.save_btn.clicked.connect(self.handle_update_meeting)
        self.page_home.refresh_meetings(); self.old_pos = None

    def create_meeting_card(self, meeting):
        card = QFrame(); card.setProperty("class", "MeetingCard"); layout = QHBoxLayout(card)
        info = QLabel(f"📅 {meeting['date']} at {meeting['start_time']}<br><b>{meeting['title']}</b>")
        info.setTextFormat(Qt.RichText); layout.addWidget(info); btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️"); edit_btn.setProperty("class", "EditButton")
        edit_btn.clicked.connect(lambda: self.open_edit_page(meeting))
        del_btn = QPushButton("🗑️"); del_btn.setProperty("class", "DeleteButton")
        del_btn.clicked.connect(lambda: self.handle_delete(meeting['id']))
        btn_layout.addWidget(edit_btn); btn_layout.addWidget(del_btn)
        if meeting['audio_path']:
            rr = QPushButton("🔄"); rr.setProperty("class", "EditButton")
            rr.clicked.connect(lambda: self.rerecord_flow(meeting['id'], meeting['title']))
            v = QPushButton("👁️"); v.setProperty("class", "ViewButton")
            v.clicked.connect(lambda: self.view_details(meeting['id'], meeting['title']))
            btn_layout.addWidget(rr); btn_layout.addWidget(v)
        else:
            rec = QPushButton("⏺"); rec.setProperty("class", "RecordButton")
            rec.clicked.connect(lambda: self.start_recording_flow(meeting['id'], meeting['title']))
            btn_layout.addWidget(rec)
        layout.addLayout(btn_layout); return card

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse(): self.old_pos = event.globalPos()
    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = QPoint(event.globalPos() - self.old_pos); self.move(self.x() + delta.x(), self.y() + delta.y()); self.old_pos = event.globalPos()
    def mouseReleaseEvent(self, event): self.old_pos = None

    def handle_save_meeting(self):
        create_meeting(self.page_new.title_input.text(), self.page_new.date_input.date().toString("yyyy-MM-dd"), self.page_new.time_input.time().toString("HH:mm"), self.page_new.notes_input.toPlainText())
        self.page_home.refresh_meetings(); self.content_area.setCurrentWidget(self.page_home)
    def open_edit_page(self, m): self.page_edit.load_meeting(m); self.content_area.setCurrentWidget(self.page_edit)
    def handle_update_meeting(self):
        update_meeting(self.page_edit.current_meeting_id, self.page_edit.title_input.text(), self.page_edit.date_input.date().toString("yyyy-MM-dd"), self.page_edit.time_input.time().toString("HH:mm"), self.page_edit.notes_input.toPlainText())
        self.page_home.refresh_meetings(); self.content_area.setCurrentWidget(self.page_home)
    def handle_delete(self, mid): delete_meeting(mid); self.page_home.refresh_meetings()
    def start_recording_flow(self, mid, t): self.content_area.setCurrentWidget(self.page_record); self.page_record.start_recording(mid, t)
    def view_details(self, mid, t): self.page_details.load_details(mid, t); self.content_area.setCurrentWidget(self.page_details)
    def rerecord_flow(self, mid, t): clear_meeting_audio_and_ai(mid); self.start_recording_flow(mid, t)