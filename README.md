# object_security_system
Sistem keamanan objek berbasis visi komputer yang menggunakan model YOLOv8 untuk memantau dan mendeteksi perubahan pada objek-objek di suatu area. Dilengkapi dengan fitur logging, alarm suara, dan akses terproteksi

# Object Security System

Sistem keamanan objek berbasis visi komputer yang memantau perubahan pada objek-objek di area tertentu menggunakan model deteksi objek YOLOv8. Jika terjadi perubahan yang tidak diotorisasi, sistem akan memicu alarm dan mencatat kejadian tersebut.

## Fitur Utama

- **Deteksi Objek Real-time**: Menggunakan model YOLOv8n untuk mendeteksi objek yang telah ditentukan.
- **Monitoring Baseline**: Membandingkan objek yang terdeteksi saat ini dengan "baseline" atau kondisi awal yang telah ditetapkan.
- **Alarm Suara**: Alarm akan berbunyi jika terdeteksi perubahan objek yang persisten (bertahan lebih lama dari ambang batas waktu yang ditentukan).
- **Sistem Log & Dokumentasi**: Setiap aktivitas penting (perubahan objek, pengaturan baseline, interaksi alarm) dicatat dalam file log harian dan disertai dengan screenshot sebagai bukti.
- **Defense Mode**: Mode khusus untuk mengamankan dan mengatur ulang baseline.
- **Akses Terproteksi**: Fitur-fitur sensitif seperti menghentikan alarm atau masuk ke mode pengaturan dilindungi oleh kode akses.
- **Pilihan Sumber Video**: Mendukung webcam laptop dan DroidCam.
- **Multithreading**: Menggunakan thread terpisah untuk input kode, sehingga tampilan video tetap responsif.

## Prasyarat

Sebelum menjalankan proyek, pastikan Anda telah menginstal pustaka-pustaka berikut:
bash
```
pip install opencv-python ultralytics pygame
```

## Struktur Proyek
object_security_system/

├── .gitignore

├── __pycache__/

├── log_activity/               # Log harian aktivitas sistem

│   └── 2025-07-23.json

├── models/

│   └── yolov8n.pt              # Model YOLOv8 yang sudah terlatih

├── screenshots_rekaman/

│   ├── authorized/             # Screenshot untuk aktivitas yang diotorisasi

│   │   └── deteksi_20250723_013720.jpg

│   └── unauthorized/           # Screenshot untuk perubahan yang tidak diotorisasi

│       └── deteksi_20250723_013251.jpg

├── venv/                       # Lingkungan virtual Python

├── alarm.mp3                   # File suara alarm

├── config.py                   # File konfigurasi sistem

├── initial_state.json          # Menyimpan state awal objek (baseline)

├── main.py                     # Skrip utama untuk menjalankan sistem

└── utils.py                    # Kumpulan fungsi utilitas

## Cara Menjalankan
### Unduh model YOLOv8n:
Jika Anda tidak menyertakan file yolov8n.pt dalam repositori, Anda perlu mengunduhnya dan menempatkannya di folder models/. Anda bisa mengunduhnya dari GitHub Ultralytics.

### Jalankan skrip utama:

Bash
```
python main.py
```
### Ikuti instruksi:

Pilih sumber video (webcam atau DroidCam).

Jendela tampilan video akan muncul.

### Gunakan tombol keyboard untuk berinteraksi:

d: Masuk/keluar Defense Mode (membutuhkan kode akses).

b: Atur baseline objek (hanya bisa dilakukan di Defense Mode atau jika belum ada baseline).

a: Masukkan kode akses untuk menghentikan alarm.

q: Keluar dari sistem.

## Konfigurasi
### File config.py berisi semua pengaturan yang dapat Anda sesuaikan, seperti:

ACCESS_CODE: Kode akses untuk fitur-fitur sensitif. PENTING: Ubah kode ini dari nilai default "123" saat pertama kali menggunakan sistem.

CONFIDENCE_THRESHOLD: Tingkat kepercayaan deteksi objek.

ALARM_PERSISTENCE_THRESHOLD: Durasi (dalam detik) perubahan harus terdeteksi sebelum alarm dipicu.

CLASSES_TO_TRACK_IDS: Daftar ID objek yang ingin dilacak.

