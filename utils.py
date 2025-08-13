import json
import datetime
import os
import cv2
import time
from collections import Counter
from ultralytics import YOLO
import threading
import pygame.mixer
import numpy as np
import config

# --- Inisialisasi Model YOLO ---
try:
    model = YOLO(config.YOLO_MODEL_PATH)
    coco_classes = model.names
except Exception as e:
    print(f"FATAL ERROR: Gagal memuat model YOLO dari {config.YOLO_MODEL_PATH}. Pastikan file ada dan tidak rusak. Error: {e}")
    exit()

# --- Inisialisasi Pygame Mixer ---
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception as e:
    print(f"Peringatan: Gagal menginisialisasi pygame.mixer: {e}. Alarm suara mungkin tidak berfungsi.")

# --- Variabel Global untuk Alarm ---
stop_alarm_event = threading.Event()
alarm_thread = None

# --- Fungsi Deteksi dan Penghitungan Objek ---
def detect_objects(frame):
    if frame is None or frame.size == 0 or np.all(frame == 0):
        return []

    if isinstance(frame, cv2.UMat):
        frame = frame.get()

    if len(frame.shape) == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    
    try:
        results = model(frame, conf=config.CONFIDENCE_THRESHOLD, verbose=False, device='cpu')
    except Exception as e:
        print(f"Error saat menjalankan model YOLO pada frame: {e}. Mungkin masalah dengan input frame atau model.")
        return []
    
    detections = []
    for r in results:
        if r.boxes:
            for box in r.boxes:
                if box.cls.numel() > 0:
                    class_id = int(box.cls[0])
                    class_name = coco_classes[class_id]
                    
                    if class_id in config.CLASSES_TO_TRACK_IDS:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append({'class': class_name, 'bbox': [x1, y1, x2, y2]})
    return detections

# --- Fungsi Hitung Jumlah Objek ---
def count_objects(detections):
    counts = Counter(d['class'] for d in detections)
    return dict(counts)

# --- Fungsi Manajemen Status Awal (Baseline) ---
def load_initial_state():
    if os.path.exists(config.INITIAL_STATE_FILE):
        with open(config.INITIAL_STATE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Peringatan: File {config.INITIAL_STATE_FILE} kosong atau rusak. Memulai dengan state kosong.")
                return {}
    return {}

def save_initial_state(state):
    with open(config.INITIAL_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Fungsi Logging Aktivitas ---
def log_activity(log_data):
    """
    Mencatat aktivitas ke dalam file log harian (YYYY-MM-DD.json).
    """
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file_path = os.path.join(config.LOG_DIR, f"{today_str}.json")
    
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    logs = []
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

    logs.append(log_data)
    with open(log_file_path, 'w') as f:
        json.dump(logs, f, indent=4)

# --- Fungsi Alarm Suara ---
def play_alarm_sound():
    if not pygame.mixer.get_init():
        print("Error: pygame.mixer belum diinisialisasi. Tidak bisa memutar alarm.")
        stop_alarm_event.set()
        return

    try:
        pygame.mixer.music.load(config.ALARM_SOUND_PATH)
        pygame.mixer.music.play(loops=-1)
        print("Alarm mulai berbunyi (looping)...")
    except Exception as e:
        print(f"Error memutar alarm sound dengan pygame.mixer: {e}. Pastikan alarm.mp3 valid dan tidak rusak.")
        stop_alarm_event.set()
        return

    while not stop_alarm_event.is_set():
        time.sleep(0.1)

def start_alarm():
    global alarm_thread
    if alarm_thread is None or not alarm_thread.is_alive():
        stop_alarm_event.clear()
        alarm_thread = threading.Thread(target=play_alarm_sound)
        alarm_thread.daemon = True
        alarm_thread.start()

def stop_alarm():
    global alarm_thread
    if alarm_thread and alarm_thread.is_alive():
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            print("Alarm dihentikan.")
        else:
            print("Peringatan: pygame.mixer tidak diinisialisasi saat mencoba menghentikan alarm.")
        stop_alarm_event.set()
        alarm_thread.join(timeout=1)
        alarm_thread = None

# --- Fungsi Screen Capture ---
def capture_screen(frame_to_save, status_type, details):
    """
    Mengambil screenshot dari frame yang diberikan dan menyimpannya
    ke dalam folder berdasarkan status (authorized/unauthorized).
    """
    # Menentukan direktori dasar tempat semua screenshot akan disimpan
    base_capture_dir = "screenshots_rekaman" # Anda bisa ubah nama folder ini jika mau

    # Menentukan sub-direktori berdasarkan status_type
    # Ini akan menjadi "screenshots_rekaman/authorized" atau "screenshots_rekaman/unauthorized"
    capture_dir = os.path.join(base_capture_dir, status_type)

    # Memastikan direktori dan sub-direktori ada
    if not os.path.exists(capture_dir):
        os.makedirs(capture_dir)

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Nama file sekarang tidak perlu menyertakan status_type karena sudah di foldernya
    # Anda bisa tetap menyertakannya jika ingin informasi ganda
    file_name = f"deteksi_{timestamp_str}.jpg" 
    
    file_path = os.path.join(capture_dir, file_name)

    # Membuat salinan frame agar tidak memodifikasi frame asli
    display_frame = frame_to_save.copy()

    # --- Bagian cv2.putText yang sebelumnya Anda komentari untuk screenshot ---
    # Pastikan bagian ini tetap dikomentari atau dihapus jika Anda tidak ingin teks di screenshot
    # font = cv2.FONT_HERSHEY_SIMPLEX
    # font_scale = 0.6
    # font_thickness = 1
    # text_color = (0, 255, 0) # Green

    # cv2.putText(display_frame, f"Time: {timestamp_str}", (10, 30), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
    # cv2.putText(display_frame, f"Status: {status_type.upper()}", (10, 60), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
    # cv2.putText(display_frame, f"Details: {details}", (10, 90), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
    # --- Akhir bagian teks di screenshot ---

    cv2.imwrite(file_path, display_frame)
    print(f"Screenshot disimpan: {file_path}", flush=True)
    return file_path

# --- Popup Notifikasi ---
def show_popup_notification(title, message):
    print(f"\n--- NOTIFIKASI: {title.upper()} ---")
    print(f"{message}\n")