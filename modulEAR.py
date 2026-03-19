import cv2
import mediapipe as mp
import numpy as np
import math
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Inisialisasi FastAPI
app = FastAPI(title="Eye Fatigue Detection API")

# Aktifkan CORS agar website frontend bisa mengambil data dari API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variabel Global untuk menyimpan state/hasil proses yang akan dikirim ke Web
fatigue_state = {
    "total_blinks": 0,
    "current_ear": 0.0,
    "dynamic_threshold": 0.0,
    "is_fatigued": False,
    "blink_rate_per_minute": 0,
    "message": "Normal"
}

# Konfigurasi EAR dan Kelelahan Mata
CONSEC_FRAMES = 2         # Jumlah frame berturut-turut mata harus tertutup agar dihitung 1 kedipan
FATIGUE_THRESHOLD = 20    # Threshold kedipan per menit (bisa disesuaikan, misal terlalu sering berkedip = lelah)

# Indeks Landmark dari MediaPipe Face Mesh untuk Mata Kiri dan Kanan
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

def euclidean_distance(p1, p2):
    """Menghitung jarak Euclidean antara 2 titik"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def eye_aspect_ratio(landmarks, eye_indices, frame_width, frame_height):
    """Menghitung Eye Aspect Ratio (EAR) dari sekumpulan indeks mata"""
    # Ambil koordinat pixel (x, y) dari landmark
    pts = []
    for idx in eye_indices:
        x = int(landmarks.landmark[idx].x * frame_width)
        y = int(landmarks.landmark[idx].y * frame_height)
        pts.append((x, y))
    
    # Hitung jarak vertikal (ada 2 pasang)
    v1 = euclidean_distance(pts[1], pts[5])
    v2 = euclidean_distance(pts[2], pts[4])
    
    # Hitung jarak horizontal
    h1 = euclidean_distance(pts[0], pts[3])
    
    # Rumus EAR
    ear = (v1 + v2) / (2.0 * h1)
    return ear, pts, v1, v2, h1

def process_camera():
    """Fungsi yang berjalan di thread terpisah untuk memproses Kamera dengan OpenCV & MediaPipe"""
    global fatigue_state
    
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1, 
        refine_landmarks=True, 
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    
    blink_counter = 0
    total_blinks = 0
    start_time = time.time()
    
    # Simpan histori (timestamp, v1, v2, h1) selama N detik terakhir
    history = {
        "left":  [],
        "right": []
    }
    
    # Durasi (detik) memori penyimpanan nilai min/max
    WINDOW_DURATION = 10.0
    
    def update_and_get_threshold(side, v1, v2, h1):
        if h1 == 0: return 0.22 # Fallback to prevent Div by 0
        
        current_time = time.time()
        
        # Tambahkan data frame ini
        history[side].append((current_time, v1, v2, h1))
        
        # Bersihkan data yang umurnya lebih dari WINDOW_DURATION (10 detik)
        # Slicing the list to keep only fresh items
        history[side] = [item for item in history[side] if current_time - item[0] <= WINDOW_DURATION]
        
        # Temukan min dan max di jendela memori yang tersisa
        v1_list = [item[1] for item in history[side]]
        v2_list = [item[2] for item in history[side]]
        h1_list = [item[3] for item in history[side]]
        
        v1_min, v1_max = min(v1_list), max(v1_list)
        v2_min, v2_max = min(v2_list), max(v2_list)
        h1_min, h1_max = min(h1_list), max(h1_list)
        
        # Mencegah pembagian dengan nol
        h1_max_val = h1_max if h1_max > 0 else h1
        h1_min_val = h1_min if h1_min > 0 else h1

        # Equation 3 dan 4 (Modified EAR formula)
        ear_closed = (v1_min + v2_min) / (2.0 * h1_max_val)
        ear_open = (v1_max + v2_max) / (2.0 * h1_min_val)
        
        # Equation 5 (Modified Threshold)
        return (ear_closed + ear_open) / 2.0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue
            
        frame = cv2.flip(frame, 1)  # Mirror frame
        h, w, _ = frame.shape
        
        cv2.imshow("Camera 1", frame)
        # Konversi BGR ke RGB untuk MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # Dapatkan EAR untuk Mata Kiri dan Kanan, beserta jarak untuk hitung Modified EAR
                left_ear, left_pts, l_v1, l_v2, l_h1 = eye_aspect_ratio(face_landmarks, LEFT_EYE, w, h)
                right_ear, right_pts, r_v1, r_v2, r_h1 = eye_aspect_ratio(face_landmarks, RIGHT_EYE, w, h)
                
                # EAR rata-rata
                avg_ear = (left_ear + right_ear) / 2.0
                fatigue_state["current_ear"] = round(avg_ear, 3)
                
                # Hitung Dynamic Threshold (Modified EAR Threshold)
                left_threshold = update_and_get_threshold("left", l_v1, l_v2, l_h1)
                right_threshold = update_and_get_threshold("right", r_v1, r_v2, r_h1)
                
                # Cek jika baru kalibrasi maka set minimal default agar program tidak macet jika mata belum berkedip
                dynamic_threshold = (left_threshold + right_threshold) / 2.0
                if dynamic_threshold > 0.4 or dynamic_threshold < 0.15:
                        dynamic_threshold = 0.22 # Fallback sebelum max/min terbentuk stabil

                fatigue_state["dynamic_threshold"] = round(dynamic_threshold, 3)
                
                # Gambar Landmark (Polygon) untuk visualisasi
                cv2.polylines(frame, [np.array(left_pts)], True, (0, 255, 0), 1)
                cv2.polylines(frame, [np.array(right_pts)], True, (0, 255, 0), 1)
                
                # Logika Deteksi Kedipan (Blink)
                if avg_ear < dynamic_threshold:
                    blink_counter += 1
                else:
                    if blink_counter >= CONSEC_FRAMES:
                        total_blinks += 1
                        fatigue_state["total_blinks"] = total_blinks
                    blink_counter = 0
                
                # Hitung Blink Rate per menit
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    blink_rate = (total_blinks / elapsed_time) * 60
                    fatigue_state["blink_rate_per_minute"] = round(blink_rate, 2)
                    
                    # Logika Gejala Astenopia / Kelelahan Mata
                    if elapsed_time > 10:  # Tunggu 10 detik kalibrasi sebelum menilai
                        if blink_rate > FATIGUE_THRESHOLD: 
                            fatigue_state["is_fatigued"] = True
                            fatigue_state["message"] = "Terdeteksi gejala kelelahan mata! (Sering Berkedip)"
                        elif blink_rate < 5: 
                            fatigue_state["is_fatigued"] = True
                            fatigue_state["message"] = "Terdeteksi gejala mata kering/lelah! (Jarang Berkedip)"
                        else:
                            fatigue_state["is_fatigued"] = False
                            fatigue_state["message"] = "Normal"

                # Tampilkan text di layar (imshow)
                cv2.putText(frame, f"EAR: {avg_ear:.2f} | Thr: {dynamic_threshold:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"Blinks: {total_blinks}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(frame, f"Rate/Min: {fatigue_state['blink_rate_per_minute']}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                status_color = (0, 0, 255) if fatigue_state["is_fatigued"] else (0, 255, 0)
                cv2.putText(frame, f"Status: {fatigue_state['message']}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        cv2.imshow("Astenopia Detection - Backend Visualizer", frame)
        
        # Tekan 'q' untuk keluar
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

# API Endpoint untuk Website Cek Status Kelelahan
@app.get("/api/fatigue-status")
def get_fatigue_status():
    """
    Endpoint ini akan dipanggil oleh Frontend (Website) setiap beberapa detik
    untuk mengecek apakah perlu menampilkan notifikasi.
    """
    return fatigue_state

def run_api():
    """Fungsi untuk menjalankan server FastAPI"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # 1. Jalankan server FastAPI (uvicorn) di thread terpisah (background)
    # Akses di http://localhost:8000/api/fatigue-status
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # 2. Jalankan proses OpenCV (kamera) di main thread karena cv2.imshow 
    # sangat membutuhkan main thread untuk me-render antarmuka GUI (Window)
    process_camera()