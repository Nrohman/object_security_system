import os

# Direktori Utama Proyek
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Path Folder Penting ---
LOG_DIR = os.path.join(BASE_DIR, 'log_activity')
CHANGES_DIR = os.path.join(BASE_DIR, 'screenshots_rekaman')
AUTHORIZED_DIR = os.path.join(CHANGES_DIR, 'authorized')
UNAUTHORIZED_DIR = os.path.join(CHANGES_DIR, 'unauthorized')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# --- File Penting ---
INITIAL_STATE_FILE = os.path.join(BASE_DIR, 'initial_state.json')
ALARM_SOUND_PATH = os.path.join(BASE_DIR, 'alarm.mp3')
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, 'yolov8n.pt')

# --- Pengaturan Sistem ---
ACCESS_CODE = "123"
CONFIDENCE_THRESHOLD = 0.5
ALARM_PERSISTENCE_THRESHOLD = 2.0

# --- Pengaturan Deteksi Objek ---
CLASSES_TO_TRACK_IDS = [
    39,  # bottle
    41,  # cup
    63,  # laptop
    64,  # mouse
    66,  # keyboard
    67,  # cell phone
    73,  # book
    74,  # clock
    76,  # scissors
]   