import cv2
import time
import datetime
import config # Pastikan file config.py ada dan berisi ACCESS_CODE dan ALARM_PERSISTENCE_THRESHOLD
import utils # Pastikan file utils.py ada dan berisi fungsi-fungsi yang dipanggil
import threading
import queue # Untuk komunikasi antar thread

# --- Fungsi untuk Memilih Sumber Video --- #
def select_video_source():
    """
    Meminta pengguna untuk memilih sumber video: webcam laptop atau DroidCam.
    Mengembalikan objek VideoCapture.
    """
    while True:
        print("\nPilih sumber video:")
        print("1. Webcam Laptop (indeks 1)")
        print("2. DroidCam (membutuhkan alamat IP)")
        choice = input("Masukkan pilihan Anda (1 atau 2): ")

        if choice == '1':
            cap = cv2.VideoCapture(1)
            if not cap.isOpened():
                print("Error: Tidak dapat membuka aliran video dari webcam laptop. Pastikan tidak sedang digunakan aplikasi lain.")
                return None
            print("Menggunakan Webcam Laptop sebagai sumber video.")
            return cap
        elif choice == '2':
            droidcam_ip = input("Masukkan alamat IP DroidCam (misal: 192.168.1.100:4747): ")
            # Format URL DroidCam, sesuaikan jika Anda menggunakan port lain atau /video
            droidcam_url = f"http://{droidcam_ip}/video" 
            # droidcam_url = f"http://192.168.100.77:4747/video"             
            print(f"Mencoba menyambung ke DroidCam di: {droidcam_url}")
            cap = cv2.VideoCapture(droidcam_url)
            if not cap.isOpened():
                print(f"Error: Tidak dapat membuka aliran video dari DroidCam di {droidcam_url}. Pastikan DroidCam aktif dan IP benar.")
                return None
            print("Menggunakan DroidCam sebagai sumber video.")
            return cap
        else:
            print("Pilihan tidak valid. Silakan masukkan 1 atau 2.")

# --- Inisialisasi Utama ---
cap = None
while cap is None:
    cap = select_video_source()
    if cap is None:
        print("Gagal menginisialisasi kamera. Mencoba lagi dalam 3 detik...")
        time.sleep(3)
# terus mencoba memilih dan menginisialisasi sumber video sampai berhasil. Jika gagal, ia akan menunggu 3 detik sebelum mencoba lagi.

cv2.namedWindow('Sistem Keamanan Objek', cv2.WINDOW_NORMAL) # Pastikan jendela dibuat di awal
# Baris ini membuat jendela tampilan OpenCV dengan nama 'Sistem Keamanan Objek'. cv2.WINDOW_NORMAL memungkinkan jendela diubah ukurannya.

current_initial_state = utils.load_initial_state()
print(f"Status baseline awal dimuat: {current_initial_state}")
# Memuat status baseline awal objek menggunakan fungsi dari modul utils

# --- Variabel Global dan Flags Status Sistem --- #
# --- Variabel Status Sistem (Akses Aman dengan Lock jika diakses antar thread) ---
alarm_active = False # Menunjukkan apakah alarm sedang berbunyi atau tidak
monitoring_active = True # Menunjukkan apakah sistem sedang aktif memantau perubahan objek, akan false jika defense_mode_active true
defense_mode_active = False # True jika sedang dalam mode pengaturan, monitoring_active false dan baseline bisa diatur ulang.
last_frame_with_change = None # Menyimpan salinan frame terakhir di mana perubahan terdeteksi. untuk mengambil screenshot yang relevan saat alarm dipicu atau dihentikan

# Variabel untuk sinkronisasi thread input kode
input_code_queue = queue.Queue() # Thread yang bertugas mengambil input kode akan "menaruh" kode yang diketik ke sini, dan thread utama akan "mengambil" kode dari sini.
input_thread = None # menyimpan objek thread yang sedang berjalan untuk mengambil input kode.
input_thread_running = False # Flag untuk menunjukkan apakah thread input sedang berjalan. Ini mencegah memulai beberapa thread input secara bersamaan

# Variabel untuk deteksi perubahan persisten
change_start_time = None # fitur penundaan alarm. Jika perubahan itu bertahan lebih lama dari ALARM_PERSISTENCE_THRESHOLD, alarm akan dipicu.

# Lock untuk melindungi akses ke variabel global yang diubah oleh thread
global_status_lock = threading.Lock()   #objek lock dari modul threading. memastikan hanya satu thread dapat memodifikasi variabel global pada satu waktu, menjaga integritas data


# --- Fungsi-fungsi Utama --- #
# --- Fungsi untuk Mengatur Baseline Secara Manual ---
# fungsi yang dipanggil ketika pengguna ingin mengatur ulang baseline objek yang harus dipantau
def set_baseline_manually(frame_to_set_from): # Menerima salinan frame video saat ini
    global current_initial_state
    detections = utils.detect_objects(frame_to_set_from) # deteksi objek frame
    current_object_counts = utils.count_objects(detections) # Menghitung jumlah objek yang terdeteksi 
    
    with global_status_lock: # Lindungi akses saat mengubah baseline
        current_initial_state = current_object_counts # diperbarui dengan hitungan objek yang baru
        utils.save_initial_state(current_initial_state) # Baseline baru disimpan
    
    print(f"Baseline awal berhasil diatur: {current_initial_state}", flush=True)
    utils.show_popup_notification("Sistem Keamanan", "Baseline awal berhasil diatur.")
    # Mencetak konfirmasi di terminal dan menampilkan notifikasi popup

    utils.log_activity({
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "event": "baseline_set",
        "status": "authorized",
        "details": f"Initial state set: {current_initial_state}",
        "capture_path": utils.capture_screen(frame_to_set_from.copy(), "authorized", "Baseline Set")
    }) # Mencatat aktivitas ini ke dalam log dan mengambil screenshot dari frame saat baseline diatur
    
# --- Fungsi yang akan dijalankan di Thread Terpisah untuk Input Kode ---
def get_code_input_threaded(): 
    global input_thread_running 
    print("\n--- MASUKKAN KODE AKSES ---", flush=True) 
    print(">>> KETIK KODE AKSES DI TERMINAL INI DAN TEKAN ENTER <<<", flush=True)
    entered_code = input("Kode Akses: ") # memblokir thread input baru, menunggu input kode akses. thread yang menampilkan kamera tidak terblokir.
    input_code_queue.put(entered_code) # cara aman ngirim data dari thread input ke thread utama
    input_thread_running = False # Tandai thread selesai
    print("--- KEMBALI KE MONITORING ---", flush=True)
# untuk dijalankan di thread terpisah. Tugasnya adalah meminta input kode akses dari pengguna

# --- Pesan Instruksi Awal --- #
print("\n--- Sistem Keamanan Objek ---")
print("Tekan 'b' untuk mengatur baseline awal (objek yang harus ada saat pertama kali start).")
print("Tekan 'd' untuk masuk/keluar dari mode pengaturan (Defense Mode).")
print("Tekan 'a' jika alarm berbunyi untuk memasukkan kode akses dan menghentikannya.")
print("Tekan 'q' untuk keluar dari sistem.")
print("-----------------------------\n")


# --- Loop Utama Aplikasi - Sistem --- #
try:
    first_detection_logged = False # Inisialisasi di sini juga

    while True: #jantung program yang akan terus berjalan
        ret, frame = cap.read() # feed video real-time. tiap iterasi, sistem membaca 1 frame dari kamera. Ada juga penanganan error jika kamera terputus.
        if not ret:
            print("Gagal membaca frame dari kamera. Mencoba inisialisasi ulang kamera...", flush=True)
            cap.release()
            # Mencoba inisialisasi ulang, tapi sekarang dengan fungsi select_video_source
            cap = None
            while cap is None:
                cap = select_video_source()
                if cap is None:
                    print("Gagal menginisialisasi ulang kamera. Mencoba lagi dalam 3 detik...")
                    time.sleep(3)
            continue
        
        # --- Deteksi dan Tampilkan Objek ---
        current_detections_list = []
        current_object_counts = {}

        try:
            current_detections_list = utils.detect_objects(frame)
            current_object_counts = utils.count_objects(current_detections_list)

            # Log deteksi awal/saat startup
            if not first_detection_logged:
                utils.log_activity({
                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                    "event": "initial_camera_detection",
                    "status": "info",
                    "details": f"Objects detected on camera startup: {current_object_counts}"
                })
                first_detection_logged = True
            
        except Exception as e:
            print(f"Error saat deteksi objek di main loop: {e}. Melanjutkan tanpa deteksi untuk frame ini.", flush=True)
            pass

        # Gambar bounding box dan label di frame untuk visualisasi
        for d in current_detections_list:
            x1, y1, x2, y2 = d['bbox']
            class_name = d['class']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # bounding box hijau objek
            cv2.putText(frame, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2) # label nama objek dan mengurangi ukuran font untuk label objek

        # --- Tampilkan Informasi Status dan Objek di Layar ---
        text_start_x = 10
        text_line_height = 20 # Mengurangi jarak antar baris untuk kerapian
        current_y_pos = 20 # Posisi Y awal untuk baris pertama
        # agar tidak tumpang tindih. Status sistem (MONITORING AKTIF, ALARM AKTIF, DEFENSE MODE) juga ditampilkan di pojok kanan atas.
        
        # Tampilkan Tanggal dan Waktu
        current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Waktu: {current_time_str}", (text_start_x, current_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        current_y_pos += text_line_height 
        
        # Tampilkan Jumlah Objek Saat Ini
        cv2.putText(frame, "Objek Saat Ini:", (text_start_x, current_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        current_y_pos += text_line_height

        # Menampilkan setiap objek terdeteksi dengan indentasi
        for obj_name, count in sorted(current_object_counts.items()):
            cv2.putText(frame, f"  - {obj_name}: {count}", (text_start_x, current_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            current_y_pos += text_line_height

        # Tambahkan sedikit spasi sebelum Baseline
        current_y_pos += 5 
        
        # Tampilkan Baseline
        with global_status_lock: # Ambil baseline dengan lock
            baseline_text = "Baseline: " + str(current_initial_state)
        cv2.putText(frame, baseline_text, (text_start_x, current_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1) # Kuning
        current_y_pos += text_line_height # Tambahkan spasi lebih setelah baseline

        # Tampilkan detail perubahan (jika ada)
        is_changed_display = False
        change_details_display = []

        # --- Perbandingan dengan Baseline dan Pemicu Alarm ---
        with global_status_lock: # Ambil status dengan lock
            is_monitoring_active = monitoring_active
            is_alarm_active_check = alarm_active 

        if is_monitoring_active and not is_alarm_active_check:
            is_current_frame_changed = False
            current_frame_change_details = []

            # Cek objek yang HILANG
            for obj_name, initial_count in current_initial_state.items():
                current_count = current_object_counts.get(obj_name, 0)
                if current_count < initial_count:
                    is_current_frame_changed = True
                    current_frame_change_details.append(f"{obj_name} hilang ({initial_count} -> {current_count})")
            
            # Cek objek yang MUNCUL
            for obj_name, current_count in current_object_counts.items():
                initial_count = current_initial_state.get(obj_name, 0)
                if current_count > initial_count:
                    is_current_frame_changed = True
                    current_frame_change_details.append(f"{obj_name} muncul ({initial_count} -> {current_count})")
            
            is_changed_display = is_current_frame_changed
            change_details_display = current_frame_change_details

            # Logika untuk Deteksi Perubahan Persisten menghindari alarm palsu karena kedipan deteksi sesaat.
            if is_current_frame_changed:
                if change_start_time is None:
                    change_start_time = time.time()
                elif (time.time() - change_start_time) > config.ALARM_PERSISTENCE_THRESHOLD:
                    print("\n!!! PERUBAHAN PERSISTEN TERDETEKSI! Mengaktifkan alarm...", flush=True)
                    utils.start_alarm()
                    with global_status_lock: # Ubah status alarm dengan lock
                        alarm_active = True
                    last_frame_with_change = frame.copy()
                    
                    change_start_time = None 

                    log_data = {
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "event": "stock_change",
                        "status": "unauthorized",
                        "initial_baseline": current_initial_state,
                        "actual_objects_at_detection": current_object_counts,
                        "change_details": ", ".join(current_frame_change_details),
                        "capture_path": utils.capture_screen(frame.copy(), "unauthorized", ", ".join(current_frame_change_details))
                    }
                    utils.log_activity(log_data)
                    utils.show_popup_notification("PERINGATAN KEAMANAN!", f"Perubahan terdeteksi: {', '.join(current_frame_change_details)}. Alarm aktif! Masukkan kode akses di terminal.")
            else:
                change_start_time = None # Reset jika tidak ada perubahan atau sudah kembali normal
        
        if is_changed_display: # Only display if changes are present in the current frame
            change_text = ", ".join(change_details_display)
            cv2.putText(frame, f"Perubahan: {change_text}", (text_start_x, current_y_pos + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1) # Cyan
            current_y_pos += text_line_height + 5

        # Indikator Status Sistem (posisi di kanan atas)
        status_text_pos_x = frame.shape[1] - 250
        status_line_height = 20
        status_y_pos = 20

        with global_status_lock: # Ambil status dengan lock
            is_alarm_active = alarm_active
            is_defense_mode_active = defense_mode_active

        if is_alarm_active:
            cv2.putText(frame, "ALARM AKTIF!", (status_text_pos_x, status_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Tekan 'a' untuk kode akses", (status_text_pos_x, status_y_pos + status_line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        elif is_defense_mode_active:
            cv2.putText(frame, "DEFENSE MODE (OFFLINE)", (status_text_pos_x, status_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, "Tekan 'd' untuk kembali monitoring", (status_text_pos_x, status_y_pos + status_line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1, cv2.LINE_AA)
            cv2.putText(frame, "Tekan 'b' untuk SET BASELINE", (status_text_pos_x, status_y_pos + 2 * status_line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "MONITORING AKTIF", (status_text_pos_x, status_y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        # --- Tampilkan Frame ke Jendela ---
        cv2.imshow('Sistem Keamanan Objek', frame) # Baris ini terus memperbarui tampilan jendela kamera dengan frame terbaru

        # --- Penanganan Input Keyboard untuk Kontrol Aplikasi ---
        key = cv2.waitKey(1) & 0xFF 
        # cara OpenCV mendengarkan tombol yang ditekan. akan menunggu 1 milidetik untuk keypress, sangat responsif.
        
        # --- Proses Kode Akses dari Thread Input (jika ada) ---
        if not input_code_queue.empty():
            entered_code = input_code_queue.get()
            
            if input_thread.name == "defense_mode_thread":
                with global_status_lock:
                    is_defense_mode_active = defense_mode_active
                    
                if entered_code == config.ACCESS_CODE:
                    with global_status_lock:
                        defense_mode_active = not defense_mode_active
                        monitoring_active = not defense_mode_active
                    
                    if defense_mode_active:
                        print("Kode akses benar. Masuk Mode Pengaturan. Monitoring non-aktif.", flush=True)
                        utils.show_popup_notification("Sistem Keamanan", "Kode benar. Anda sekarang di Mode Pengaturan. Tekan 'b' untuk atur baseline baru.")
                        utils.log_activity({
                            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                            "event": "defense_mode_enter",
                            "status": "authorized",
                            "details": "User entered defense mode."
                        })
                    else:
                        print("Keluar dari Mode Pengaturan. Monitoring aktif kembali.", flush=True)
                        utils.show_popup_notification("Sistem Keamanan", "Keluar dari Mode Pengaturan. Monitoring aktif kembali.")
                        utils.log_activity({
                            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                            "event": "defense_mode_exit",
                            "status": "authorized",
                            "details": "User exited defense mode. Monitoring resumed."
                        })
                else:
                    print("Kode akses salah. Tidak bisa mengubah Mode Pengaturan.", flush=True)
                    utils.show_popup_notification("Sistem Keamanan", "Kode salah. Tidak bisa masuk Mode Pengaturan.")
                    utils.log_activity({
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "event": "defense_mode_attempt",
                        "status": "unauthorized",
                        "details": "Attempt to enter defense mode with incorrect code."
                    })
            
            elif input_thread.name == "alarm_code_thread":
                with global_status_lock:
                    is_alarm_active = alarm_active

                if entered_code == config.ACCESS_CODE:
                    print("Kode akses benar. Alarm dihentikan.", flush=True)
                    utils.stop_alarm()
                    with global_status_lock:
                        alarm_active = False
                    
                    if last_frame_with_change is not None:
                        new_state_detections = utils.detect_objects(last_frame_with_change)
                        new_initial_state = utils.count_objects(new_state_detections) 
                        with global_status_lock:
                            current_initial_state = new_initial_state
                            utils.save_initial_state(current_initial_state)
                        print(f"Baseline berhasil diperbarui: {current_initial_state}", flush=True)
                        
                        utils.log_activity({
                            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                            "event": "alarm_acknowledged",
                            "status": "authorized",
                            "details": "Alarm acknowledged. Baseline updated to current state.",
                            "actual_objects_after_auth": current_initial_state,
                            "capture_path": utils.capture_screen(last_frame_with_change.copy(), "authorized", "Changes Authorized (Alarm)")
                        })
                        utils.show_popup_notification("Sistem Keamanan", "Perubahan diotorisasi. Baseline diperbarui.")
                    else:
                        utils.show_popup_notification("Sistem Keamanan", "Kode benar, tapi frame untuk update baseline tidak ditemukan.")
                        utils.log_activity({
                            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                            "event": "alarm_acknowledged_no_frame",
                            "status": "authorized",
                            "details": "Kode benar, tapi frame untuk update baseline tidak ditemukan."
                        })

                else:
                    print("Kode akses salah. Alarm tetap aktif.", flush=True)
                    utils.show_popup_notification("Sistem Keamanan", "Kode akses salah. Alarm tetap aktif.")
                    utils.log_activity({
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "event": "alarm_code_incorrect",
                        "status": "unauthorized",
                        "details": "Incorrect code entered while alarm was active."
                    })
            input_thread = None
            input_thread_running = False

        # --- Penanganan Keypress ---
        if key == ord('q'):
            print("Menghentikan sistem...", flush=True)
            break

        elif key == ord('b'):
            with global_status_lock:
                is_defense_mode_active = defense_mode_active
                is_initial_state_set = bool(current_initial_state)

            if not input_thread_running:
                if is_defense_mode_active:
                    set_baseline_manually(frame.copy())
                elif not is_initial_state_set:
                    set_baseline_manually(frame.copy())
                else:
                    print("Tekan 'd' dan masukkan kode akses untuk masuk mode pengaturan baseline terlebih dahulu.", flush=True)
            else:
                print("Sistem sedang menunggu input kode. Mohon tunggu.", flush=True)

        elif key == ord('d'):
            if not input_thread_running:
                with global_status_lock:
                    is_defense_mode_active = defense_mode_active

                if not is_defense_mode_active:
                    input_thread_running = True
                    input_thread = threading.Thread(target=get_code_input_threaded, name="defense_mode_thread")
                    input_thread.daemon = True
                    input_thread.start()
                else:
                    input_thread_running = True
                    input_thread = threading.Thread(target=get_code_input_threaded, name="defense_mode_thread")
                    input_thread.daemon = True
                    input_thread.start()
            else:
                print("Sistem sedang menunggu input kode. Mohon tunggu.", flush=True)

        elif key == ord('a'):
            with global_status_lock:
                is_alarm_active = alarm_active

            if is_alarm_active:
                if not input_thread_running:
                    input_thread_running = True
                    input_thread = threading.Thread(target=get_code_input_threaded, name="alarm_code_thread")
                    input_thread.daemon = True
                    input_thread.start()
                else:
                    print("Sistem sedang menunggu input kode. Mohon tunggu.", flush=True)
            else:
                print("Alarm tidak aktif saat ini.", flush=True)

# blok penanganan error, menekan Ctrl+C di terminal, program akan menangkap KeyboardInterrupt dan menjalankan blok finally.
except KeyboardInterrupt:
    print("\nKeyboardInterrupt terdeteksi. Menghentikan sistem dengan paksa.", flush=True)

# --- Cleanup (Setelah Loop Berhenti) ---
print("Membersihkan sumber daya...", flush=True)
utils.stop_alarm() # Memastikan alarm berhenti jika masih berbunyi
if cap.isOpened(): # Melepaskan kamera agar aplikasi lain bisa menggunakannya
    cap.release() # Menutup semua jendela OpenCV 
cv2.destroyAllWindows() 
print("Sistem keamanan objek telah dimatikan.", flush=True) # Mencetak pesan konfirmasi bahwa sistem telah dimatikan