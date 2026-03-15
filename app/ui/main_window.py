import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QStackedWidget, QLineEdit, 
                               QTextEdit, QDateEdit, QTimeEdit, QFrame, QMessageBox, 
                               QScrollArea, QGraphicsOpacityEffect, QCalendarWidget, QComboBox)
from PySide6.QtCore import Qt, QDate, QTime, QTimer, QThread, Signal, QPoint, QPropertyAnimation, QEasingCurve, QObject
from PySide6.QtGui import QPainter, QColor, QLinearGradient

from app.database.queries import (create_meeting, get_all_meetings, update_meeting_audio, 
                                  delete_meeting, save_ai_results, get_meeting_details, 
                                  update_meeting, clear_meeting_audio_and_ai, search_meetings)
from app.audio.recorder import AudioRecorder
from app.config import RECORDINGS_DIR
from app.ai.transcriber import transcribe_audio
from app.ai.summarizer import generate_meeting_summary

# --- Premium Stylesheet (Dark Header, Light Body, Gradient Pill, Rounded Calendar) ---
STYLESHEET = """
QMainWindow { background-color: transparent; }
#MainContainer { background-color: #F8F9FA; border-radius: 20px; }

#TitleBar { background-color: #1E1E20; border-top-left-radius: 20px; border-top-right-radius: 20px; min-height: 40px; }
#TopNavBar { background-color: #1E1E20; padding-bottom: 20px; }
#TitleLabel { color: #888888; font-size: 12px; margin-left: 20px; font-weight: bold; }
#WindowButtons { color: #888888; background: transparent; border: none; padding: 10px 18px; font-size: 16px; }
#WindowButtons:hover { color: white; }
#CloseButton:hover { background-color: #E81123; color: white; border-top-right-radius: 20px; }

#NavPillContainer { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:0.5 #EC4899, stop:1 #F97316); border-radius: 25px; }

QPushButton.PrimaryAction { background-color: #8B5CF6; color: white; border-radius: 8px; padding: 10px 20px; font-weight: bold; border: none; }
QPushButton.RecordButton { background-color: #EC4899; color: white; border-radius: 8px; padding: 8px 16px; font-weight: bold; border: none; }
QPushButton.EditButton { background-color: transparent; color: #8B5CF6; font-weight: bold; padding: 8px; border: 1px solid #8B5CF6; border-radius: 6px; }
QPushButton.EditButton:hover { background-color: #EDE9FE; }
QPushButton.ViewButton { background-color: #10B981; color: white; font-weight: bold; padding: 8px 15px; border-radius: 6px; }
QPushButton.ViewButton:hover { background-color: #059669; }
QPushButton.DeleteButton { background-color: transparent; color: #999999; border: 1px solid #DDDDDD; border-radius: 8px; padding: 8px; }
QPushButton.DeleteButton:hover { color: #E53935; border-color: #E53935; }

QLabel.Header { font-size: 24px; font-weight: bold; color: #1E1E20; padding-bottom: 10px; }
QLabel.CategoryHeader { font-size: 15px; font-weight: bold; color: #8B5CF6; margin-top: 15px; padding-bottom: 5px; text-transform: uppercase;}
QLabel.CategoryHeaderFinished { font-size: 15px; font-weight: bold; color: #F97316; margin-top: 25px; padding-bottom: 5px; text-transform: uppercase;}
QLabel.Timer { font-size: 64px; font-weight: bold; color: #EC4899; }

QFrame.MeetingCard { background-color: white; border-radius: 12px; border: 1px solid #EAEAEA; margin-bottom: 8px; }
QScrollArea { border: none; background-color: transparent; }
QScrollArea QWidget { background-color: transparent; }

QLineEdit, QTextEdit, QDateEdit, QTimeEdit { border: 1px solid #EAEAEA; border-radius: 8px; padding: 12px; background-color: white; font-size: 14px; }

/* Rounded Mini Calendar */
QCalendarWidget { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #EAEAEA; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #F8F9FA; border-top-left-radius: 15px; border-top-right-radius: 15px; border-bottom: 1px solid #EAEAEA; padding: 5px; }
QCalendarWidget QToolButton { color: #1E1E20; font-weight: bold; border-radius: 6px; background-color: transparent; padding: 4px; }
QCalendarWidget QToolButton:hover { background-color: #EAEAEA; }
QCalendarWidget QAbstractItemView:enabled { color: #1E1E20; selection-background-color: #8B5CF6; selection-color: white; border-bottom-left-radius: 15px; border-bottom-right-radius: 15px; outline: none; }
QCalendarWidget QAbstractItemView:disabled { color: #CCCCCC; }

/* Dual Dropdowns */
QComboBox { border: 1px solid #EAEAEA; border-radius: 8px; padding: 10px; background-color: white; font-size: 13px; font-weight: bold; color: #1E1E20; min-width: 220px;}
QComboBox::drop-down { border: none; width: 30px; }
QComboBox QAbstractItemView { background: white; border: 1px solid #EAEAEA; border-radius: 8px; selection-background-color: #8B5CF6; selection-color: white; outline: none; }
"""

# --- AUDIO WAVEFORM VISUALIZER ---
class AudioVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(100); self.setMinimumWidth(400)
        self.bars = [0] * 40; self.target_bars = [0] * 40
        self.anim_timer = QTimer(); self.anim_timer.timeout.connect(self.update_animation); self.anim_timer.start(30) 

    def update_volume(self, volume):
        val = min(int(volume * 2500), 100) 
        self.target_bars.pop(0); self.target_bars.append(val)

    def update_animation(self):
        for i in range(len(self.bars)):
            diff = self.target_bars[i] - self.bars[i]
            self.bars[i] += diff * 0.3 
        self.update()

    def reset(self):
        self.bars = [0] * 40; self.target_bars = [0] * 40; self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = (w / len(self.bars)) - 3
        
        for i, val in enumerate(self.bars):
            bar_h = max((val / 100.0) * h, 6)
            x = i * (bar_w + 3); y = (h - bar_h) / 2
            
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, QColor("#8B5CF6")); grad.setColorAt(1, QColor("#F97316"))
            
            painter.setBrush(grad); painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), int(bar_w/2), int(bar_w/2))

class VolumeBridge(QObject): volume_updated = Signal(float)

# --- CUSTOM ANIMATED BUTTON (The Expanding Pill Effect) ---
class AnimatedNavButton(QPushButton):
    def __init__(self, icon_text, full_text):
        super().__init__(icon_text)
        self.icon_text = icon_text; self.full_text = full_text; self.is_active = None
        
        self.anim_min = QPropertyAnimation(self, b"minimumWidth")
        self.anim_max = QPropertyAnimation(self, b"maximumWidth")
        for anim in [self.anim_min, self.anim_max]:
            anim.setDuration(300); anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setFixedHeight(40); self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        
        if active:
            self.setText(f"{self.icon_text}  {self.full_text}")
            self.setStyleSheet("border-radius: 20px; font-weight: bold; font-size: 13px; color: white; background-color: rgba(255, 255, 255, 0.3);")
            self.anim_min.setStartValue(50); self.anim_min.setEndValue(120)
            self.anim_max.setStartValue(50); self.anim_max.setEndValue(120)
        else:
            self.setText(self.icon_text)
            self.setStyleSheet("border-radius: 20px; font-weight: bold; font-size: 16px; color: white; background-color: transparent;")
            self.anim_min.setStartValue(120); self.anim_min.setEndValue(50)
            self.anim_max.setStartValue(120); self.anim_max.setEndValue(50)
            
        self.anim_min.start(); self.anim_max.start()

# --- Page Cross-Fade Animation ---
class AnimatedStackedWidget(QStackedWidget):
    def transition_to(self, index):
        if self.currentIndex() == index: return
        eff = QGraphicsOpacityEffect(self.widget(index))
        self.widget(index).setGraphicsEffect(eff)
        self.fade_anim = QPropertyAnimation(eff, b"opacity")
        self.fade_anim.setDuration(400); self.fade_anim.setStartValue(0); self.fade_anim.setEndValue(1); self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setCurrentIndex(index); self.fade_anim.start()

class AIWorker(QThread):
    finished_data = Signal(int, str, str, str); error = Signal(str)
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
            lbl = QLabel(lbl_text); lbl.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px; color: #1E1E20;"); self.content_layout.addWidget(lbl)
            txt = QTextEdit(); txt.setReadOnly(True); setattr(self, attr_name, txt); self.content_layout.addWidget(txt)
        scroll.setWidget(content_widget); layout.addWidget(scroll)

    def load_details(self, meeting_id, title):
        self.header.setText(f"Details: {title}")
        data = get_meeting_details(meeting_id)
        self.summary_text.setText(data['summary']); self.decisions_text.setText(data['decisions']); self.transcript_text.setText(data['transcript'])

# --- RE-ENGINEERED RECORDING PAGE ---
class RecordingPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.current_meeting_id = None; self.recorder = None; self.seconds_elapsed = 0; self.is_recording = False
        layout = QVBoxLayout(self); layout.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel("Meeting Title"); self.title_label.setProperty("class", "Header"); layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        
        # Dual Dropdowns!
        selectors_layout = QHBoxLayout()
        selectors_layout.setAlignment(Qt.AlignCenter)
        
        mic_layout = QVBoxLayout()
        mic_lbl = QLabel("🎤 Select Microphone"); mic_lbl.setStyleSheet("font-weight:bold; color:#888; font-size: 12px;")
        self.mic_combo = QComboBox()
        mic_layout.addWidget(mic_lbl); mic_layout.addWidget(self.mic_combo)
        
        play_layout = QVBoxLayout()
        play_lbl = QLabel("🔊 Select System Audio"); play_lbl.setStyleSheet("font-weight:bold; color:#888; font-size: 12px;")
        self.play_combo = QComboBox()
        play_layout.addWidget(play_lbl); play_layout.addWidget(self.play_combo)
        
        selectors_layout.addLayout(mic_layout); selectors_layout.addSpacing(20); selectors_layout.addLayout(play_layout)
        layout.addLayout(selectors_layout)
        
        self.timer_label = QLabel("00:00"); self.timer_label.setProperty("class", "Timer"); layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        
        self.visualizer = AudioVisualizer(); layout.addWidget(self.visualizer, alignment=Qt.AlignCenter)
        
        self.status_label = QLabel(""); layout.addWidget(self.status_label, alignment=Qt.AlignCenter)
        self.action_btn = QPushButton("▶️ Start Recording"); self.action_btn.setMinimumWidth(200)
        self.action_btn.clicked.connect(self.toggle_recording); layout.addWidget(self.action_btn, alignment=Qt.AlignCenter)
        
        self.timer = QTimer(); self.timer.timeout.connect(self.update_timer)
        self.vol_bridge = VolumeBridge(); self.vol_bridge.volume_updated.connect(self.visualizer.update_volume)

    def load_page(self, meeting_id, meeting_title):
        self.current_meeting_id = meeting_id; self.title_label.setText(f"Recording: {meeting_title}")
        self.seconds_elapsed = 0; self.timer_label.setText("00:00")
        self.is_recording = False
        self.action_btn.setText("▶️ Start Recording"); self.action_btn.setStyleSheet("background-color: #10B981; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        self.action_btn.setEnabled(True)
        self.status_label.setText("Select your sources and press Start.")
        self.visualizer.reset()
        
        self.mic_combo.clear(); self.play_combo.clear()
        
        # Explicit "None" options
        self.mic_combo.addItem("None (Muted)", None)
        self.play_combo.addItem("None (Muted)", None)
        
        from app.audio.recorder import get_audio_devices
        mics, playbacks = get_audio_devices()
        
        for m in mics: self.mic_combo.addItem(m['name'], m['id'])
        for p in playbacks: self.play_combo.addItem(p['name'], p['id'])
        
        if mics: self.mic_combo.setCurrentIndex(1) # Default select the first mic
            
        self.mic_combo.setEnabled(True); self.play_combo.setEnabled(True)

    def toggle_recording(self):
        if not self.is_recording:
            # START RECORDING
            mic_id = self.mic_combo.currentData()
            play_id = self.play_combo.currentData()
            
            if mic_id is None and play_id is None:
                QMessageBox.warning(self, "No Audio", "Please select at least one audio source!")
                return
                
            filename = os.path.join(RECORDINGS_DIR, f"meeting_{self.current_meeting_id}.wav")
            def v_cb(rms): self.vol_bridge.volume_updated.emit(rms)
            
            self.recorder = AudioRecorder(filename, mic_id=mic_id, play_id=play_id, volume_callback=v_cb)
            
            try:
                self.recorder.start(); self.timer.start(1000)
                self.is_recording = True
                self.action_btn.setText("⏹ Stop Recording")
                self.action_btn.setStyleSheet("background-color: #EC4899; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
                self.status_label.setText("Recording in progress...")
                self.mic_combo.setEnabled(False); self.play_combo.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "Audio Error", f"Failed to start audio stream: {e}")
        else:
            # STOP RECORDING
            self.timer.stop(); self.action_btn.setEnabled(False)
            self.status_label.setText("Processing AI... Please wait.")
            if self.recorder:
                p = self.recorder.stop()
                update_meeting_audio(self.current_meeting_id, p)
                self.ai_worker = AIWorker(self.current_meeting_id, p)
                self.ai_worker.finished_data.connect(self.on_ai_finished); self.ai_worker.start()

    def update_timer(self):
        self.seconds_elapsed += 1; mins, secs = divmod(self.seconds_elapsed, 60); self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def on_ai_finished(self, meeting_id, transcript, summary, decisions):
        save_ai_results(meeting_id, transcript, summary, decisions)
        self.status_label.setText(""); self.main_window.page_home.refresh_meetings(); self.main_window.switch_tab(0)

class HomePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.main_layout = QVBoxLayout(self) 
        header = QLabel("Dashboard"); header.setProperty("class", "Header"); self.main_layout.addWidget(header)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.viewport().setStyleSheet("background-color: transparent;") 
        content_widget = QWidget(); content_widget.setStyleSheet("background-color: transparent;")
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
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self); header = QLabel("New Meeting"); header.setProperty("class", "Header"); layout.addWidget(header)
        self.title_input = QLineEdit(); self.title_input.setPlaceholderText("Title"); layout.addWidget(self.title_input)
        
        self.date_input = QDateEdit(); self.date_input.setDate(QDate.currentDate()); self.date_input.setCalendarPopup(True); layout.addWidget(self.date_input)
        
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
        
        self.date_input = QDateEdit(); self.date_input.setCalendarPopup(True); layout.addWidget(self.date_input)
        
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
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.viewport().setStyleSheet("background-color: transparent;") 
        content_widget = QWidget(); content_widget.setStyleSheet("background-color: transparent;")
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

        # 1. Dark Title Bar
        self.title_bar = QFrame(); self.title_bar.setObjectName("TitleBar")
        title_layout = QHBoxLayout(self.title_bar)
        title_label = QLabel(" AI Meeting Assistant"); title_label.setObjectName("TitleLabel")
        self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("CloseButton"); self.btn_close.setProperty("id", "WindowButtons")
        self.btn_min = QPushButton("—"); self.btn_min.setObjectName("WindowButtons"); self.btn_min.setProperty("id", "WindowButtons")
        title_layout.addWidget(title_label); title_layout.addStretch(); title_layout.addWidget(self.btn_min); title_layout.addWidget(self.btn_close)
        outer_layout.addWidget(self.title_bar)

        # 2. Top Animated Navigation Pill
        self.nav_bar = QFrame(objectName="TopNavBar")
        n_layout = QHBoxLayout(self.nav_bar)
        
        self.pill_frame = QFrame(objectName="NavPillContainer")
        self.pill_frame.setFixedHeight(50) 
        pill_layout = QHBoxLayout(self.pill_frame)
        pill_layout.setContentsMargins(5, 5, 5, 5); pill_layout.setSpacing(5)
        
        self.btn_home = AnimatedNavButton("🏠", "HOME")
        self.btn_new = AnimatedNavButton("➕", "NEW")
        self.btn_search = AnimatedNavButton("🔍", "SEARCH")
        
        self.btn_home.clicked.connect(lambda *args: self.switch_tab(0))
        self.btn_new.clicked.connect(lambda *args: self.switch_tab(1))
        self.btn_search.clicked.connect(lambda *args: self.switch_tab(2))
        
        pill_layout.addWidget(self.btn_home); pill_layout.addWidget(self.btn_new); pill_layout.addWidget(self.btn_search)
        n_layout.addStretch(); n_layout.addWidget(self.pill_frame); n_layout.addStretch()
        outer_layout.addWidget(self.nav_bar)

        # 3. Content Area
        self.content_area = AnimatedStackedWidget()
        self.content_area.setContentsMargins(30, 10, 30, 30) 
        
        self.page_home = HomePage(self); self.page_new = CreateMeetingPage(self); self.page_edit = EditMeetingPage() 
        self.page_search = SearchPage(self); self.page_record = RecordingPage(self); self.page_details = DetailsPage(self)
        
        for p in [self.page_home, self.page_new, self.page_search, self.page_edit, self.page_record, self.page_details]: 
            self.content_area.addWidget(p)
            
        outer_layout.addWidget(self.content_area)

        # Actions
        self.btn_close.clicked.connect(self.close); self.btn_min.clicked.connect(self.showMinimized)
        self.page_new.save_btn.clicked.connect(self.handle_save_meeting); self.page_edit.save_btn.clicked.connect(self.handle_update_meeting)
        
        self.switch_tab(0); self.old_pos = None

    def switch_tab(self, index):
        self.btn_home.set_active(index == 0)
        self.btn_new.set_active(index == 1)
        self.btn_search.set_active(index == 2)
        
        if index == 0: self.page_home.refresh_meetings()
        self.content_area.transition_to(index)

    def create_meeting_card(self, meeting):
        card = QFrame(); card.setProperty("class", "MeetingCard"); layout = QHBoxLayout(card)
        info = QLabel(f"📅 {meeting['date']} at {meeting['start_time']}<br><span style='font-size:16px; color:#1E1E20;'><b>{meeting['title']}</b></span>")
        info.setTextFormat(Qt.RichText); layout.addWidget(info); btn_layout = QHBoxLayout()
        
        edit_btn = QPushButton("✏️"); edit_btn.setProperty("class", "EditButton")
        edit_btn.clicked.connect(lambda *args: self.open_edit_page(meeting))
        
        del_btn = QPushButton("🗑️"); del_btn.setProperty("class", "DeleteButton")
        del_btn.clicked.connect(lambda *args: self.handle_delete(meeting['id']))
        
        btn_layout.addWidget(edit_btn); btn_layout.addWidget(del_btn)
        
        if meeting.get('audio_path'):
            rr = QPushButton("🔄"); rr.setProperty("class", "EditButton")
            rr.clicked.connect(lambda *args: self.rerecord_flow(meeting['id'], meeting['title']))
            v = QPushButton("👁️ Details"); v.setProperty("class", "ViewButton")
            v.clicked.connect(lambda *args: self.view_details(meeting['id'], meeting['title']))
            btn_layout.addWidget(rr); btn_layout.addWidget(v)
        else:
            rec = QPushButton("⏺ Record"); rec.setProperty("class", "RecordButton")
            rec.clicked.connect(lambda *args: self.start_recording_flow(meeting['id'], meeting['title']))
            btn_layout.addWidget(rec)
        layout.addLayout(btn_layout); return card

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (self.title_bar.underMouse() or self.nav_bar.underMouse()): self.old_pos = event.globalPos()
    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = QPoint(event.globalPos() - self.old_pos); self.move(self.x() + delta.x(), self.y() + delta.y()); self.old_pos = event.globalPos()
    def mouseReleaseEvent(self, event): self.old_pos = None

    def handle_save_meeting(self):
        create_meeting(self.page_new.title_input.text(), self.page_new.date_input.date().toString("yyyy-MM-dd"), self.page_new.time_input.time().toString("HH:mm"), self.page_new.notes_input.toPlainText())
        self.page_home.refresh_meetings(); self.switch_tab(0)
        
    def open_edit_page(self, m): 
        self.btn_home.set_active(False); self.btn_new.set_active(False); self.btn_search.set_active(False)
        self.page_edit.load_meeting(m); self.content_area.transition_to(3) 
        
    def handle_update_meeting(self):
        update_meeting(self.page_edit.current_meeting_id, self.page_edit.title_input.text(), self.page_edit.date_input.date().toString("yyyy-MM-dd"), self.page_edit.time_input.time().toString("HH:mm"), self.page_edit.notes_input.toPlainText())
        self.page_home.refresh_meetings(); self.switch_tab(0)
        
    def handle_delete(self, mid): 
        delete_meeting(mid); self.page_home.refresh_meetings()
        
    def start_recording_flow(self, mid, t): 
        self.btn_home.set_active(False); self.btn_new.set_active(False); self.btn_search.set_active(False)
        self.page_record.load_page(mid, t); self.content_area.transition_to(4) 
        
    def view_details(self, mid, t): 
        self.btn_home.set_active(False); self.btn_new.set_active(False); self.btn_search.set_active(False)
        self.page_details.load_details(mid, t); self.content_area.transition_to(5) 
        
    def rerecord_flow(self, mid, t): 
        clear_meeting_audio_and_ai(mid); self.start_recording_flow(mid, t)