import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
# ------------------------------------------

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow      
from app.database.db_setup import initialize_db 

def main():
    # 1. Initialize the local database if it doesn't exist
    print("Checking database...")
    initialize_db()
    
    # 2. Ensure data folders exist for recordings
    os.makedirs('data/recordings', exist_ok=True)

    # 3. Launch the UI
    app = QApplication(sys.argv)
    
    # Set global font
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
