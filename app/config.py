import os
from dotenv import load_dotenv

# ---------------------------------------------------------
# Environment Setup
# ---------------------------------------------------------
# Load environment variables from the .env file in the root directory
load_dotenv()

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ---------------------------------------------------------
# Application Paths
# ---------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(APP_DIR, '..'))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
RECORDINGS_DIR = os.path.join(DATA_DIR, 'recordings')
DB_PATH = os.path.join(DATA_DIR, 'database.sqlite')

# Ensure data directories exist upon startup
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# ---------------------------------------------------------
# Audio Recording Constants
# ---------------------------------------------------------
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_FORMAT = ".wav"

# ---------------------------------------------------------
# AI Model Constants
# ---------------------------------------------------------
SUMMARY_MODEL = "gemini-2.5-flash" 

# ---------------------------------------------------------
# UI Constants
# ---------------------------------------------------------
APP_NAME = "AI Meeting Assistant"
APP_VERSION = "0.1.0"