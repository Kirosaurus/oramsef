import cv2
import mediapipe as mp
import numpy as np
import math
import threading
import time
import base64
import queue
import sys
import os

# Menambahkan parent directory ke sys.path untuk import modulDist
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__) + "Module", "..")))
import modulDist

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Inisialisasi FastAPI
app = FastAPI(title="Eye Fatigue Detection API")

# === GUI Debugging Thread ===
# Window imshow dijalankan di thread terpisah agar tidak memblokir (stutter) aliran WebSocket yang berjalan secara asynchronous.
display_queue = queue.Queue(maxsize=1)

def display_thread():
    while True:
        frame = display_queue.get()
        if frame is None:
            break
        if isinstance(frame, str) and frame == "CLOSE":
            cv2.destroyAllWindows()
            continue
        try:
            cv2.imshow("Backend Debugging - OpenCV", frame)
            # Tangkap tombol 'q' meskipun dari debugger window
            if cv2.waitKey(1) & 0xFF == ord('q'):
                pass
        except Exception:
            pass

# Jalankan thread display sebagai daemon (langsung mati ketika server ditutup)
threading.Thread(target=display_thread, daemon=True).start()
# ============================

# Aktifkan CORS agar website frontend bisa mengambil data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurasi EAR dan Kelelahan Mata
CONSEC_FRAMES = 2
DROWSINESS_FRAMES = 30
CVS_UPPER_LIMIT = 17
CVS_LOWER_LIMIT = 9

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

def euclidean_distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def eye_aspect_ratio(landmarks, eye_indices, frame_width, frame_height):
    pts = []
    for idx in eye_indices:
        x = int(landmarks.landmark[idx].x * frame_width)
        y = int(landmarks.landmark[idx].y * frame_height)
        pts.append((x, y))
    
    v1 = euclidean_distance(pts[1], pts[5])
    v2 = euclidean_distance(pts[2], pts[4])
    h1 = euclidean_distance(pts[0], pts[3])
    ear = (v1 + v2) / (2.0 * h1)
    return ear, pts, v1, v2, h1

# === Class Detektor (Dibuat Class Agar Mendukung Banyak Sesi WebSocket Sekaligus) ===
class FatigueDetector:
    def __init__(self):
        self.blink_counter = 0
        self.total_blinks = 0
        self.start_time = time.time()
        self.blink_timestamps = []
        self.history = {"left": [], "right": []}
        self.WINDOW_DURATION = 10.0
        
        self.state = {
            "total_blinks": 0,
            "current_ear": 0.0,
            "dynamic_threshold": 0.0,
            "is_fatigued": False,
            "is_drowsy": False,
            "blink_rate_per_minute": 0,
            "message": "Menunggu...",
            "is_calibrated": False,
            "distance": 0.0,
            "focal_length": 0.0
        }
        self.calibrate_requested = False
        self.focal_length = 0.0
        self.KNOWN_WIDTH = 6.3 # Estimasi ICD (Inner Canthal Distance) rata-rata manusia
        self.KNOWN_DISTANCE = 50.0 # Asumsi estimasi jarak lengan saat kalibrasi

    def update_and_get_threshold(self, side, v1, v2, h1):
        if h1 == 0: return 0.22
        current_time = time.time()
        self.history[side].append((current_time, v1, v2, h1))
        self.history[side] = [item for item in self.history[side] if current_time - item[0] <= self.WINDOW_DURATION]
        
        v1_list = [item[1] for item in self.history[side]]
        v2_list = [item[2] for item in self.history[side]]
        h1_list = [item[3] for item in self.history[side]]
        
        v1_min, v1_max = min(v1_list), max(v1_list)
        v2_min, v2_max = min(v2_list), max(v2_list)
        h1_min, h1_max = min(h1_list), max(h1_list)
        
        h1_max_val = h1_max if h1_max > 0 else h1
        h1_min_val = h1_min if h1_min > 0 else h1

        ear_closed = (v1_min + v2_min) / (2.0 * h1_max_val)
        ear_open = (v1_max + v2_max) / (2.0 * h1_min_val)
        return (ear_closed + ear_open) / 2.0

    def process_frame(self, frame, face_mesh):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_ear, left_pts, l_v1, l_v2, l_h1 = eye_aspect_ratio(face_landmarks, LEFT_EYE, w, h)
                right_ear, right_pts, r_v1, r_v2, r_h1 = eye_aspect_ratio(face_landmarks, RIGHT_EYE, w, h)
                
                # Menghitung Jarak Wajah Menggunakan ICD (Inner Canthal Distance)
                icd_pixel_width = euclidean_distance(left_pts[3], right_pts[0]) # Landmark 133(kiri) ke 362(kanan)
                
                # Cek jika permintan kalibrasi masuk
                if self.calibrate_requested:
                    self.focal_length = modulDist.calculate_focal_length(self.KNOWN_DISTANCE, self.KNOWN_WIDTH, icd_pixel_width)
                    self.state["is_calibrated"] = True
                    self.state["focal_length"] = self.focal_length
                    self.calibrate_requested = False
                    self.start_time = time.time() # Reset perhitungan waktu mulai karena baru aktif
                
                if not self.state["is_calibrated"]:
                    self.state["message"] = "Menunggu Kalibrasi..."
                    cv2.polylines(frame, [np.array(left_pts)], True, (0, 255, 255), 1)
                    cv2.polylines(frame, [np.array(right_pts)], True, (0, 255, 255), 1)
                    return self.state, frame
                
                # --- Jika Sudah Dikalibrasi ---
                avg_ear = (left_ear + right_ear) / 2.0
                self.state["current_ear"] = round(avg_ear, 3)
                
                left_threshold = self.update_and_get_threshold("left", l_v1, l_v2, l_h1)
                right_threshold = self.update_and_get_threshold("right", r_v1, r_v2, r_h1)
                
                dynamic_threshold = (left_threshold + right_threshold) / 2.0
                if dynamic_threshold > 0.4 or dynamic_threshold < 0.15:
                    dynamic_threshold = 0.22 

                self.state["dynamic_threshold"] = round(dynamic_threshold, 3)
                
                dist = modulDist.distance_to_camera(self.focal_length, self.KNOWN_WIDTH, icd_pixel_width)
                self.state["distance"] = round(dist, 1)
                
                cv2.polylines(frame, [np.array(left_pts)], True, (0, 255, 0), 1)
                cv2.polylines(frame, [np.array(right_pts)], True, (0, 255, 0), 1)
                
                current_time = time.time()
                if avg_ear < dynamic_threshold:
                    self.blink_counter += 1
                    if self.blink_counter >= DROWSINESS_FRAMES:
                        self.state["is_drowsy"] = True
                else:
                    if self.blink_counter >= CONSEC_FRAMES:
                        self.total_blinks += 1
                        self.state["total_blinks"] = self.total_blinks
                        self.blink_timestamps.append(current_time)
                    self.blink_counter = 0
                    self.state["is_drowsy"] = False
                
                self.blink_timestamps = [t for t in self.blink_timestamps if current_time - t <= 60.0]
                
                elapsed_time = current_time - self.start_time
                if elapsed_time > 0:
                    if elapsed_time >= 60:
                        blink_rate = len(self.blink_timestamps)
                    else:
                        blink_rate = (len(self.blink_timestamps) / elapsed_time) * 60
                        
                    self.state["blink_rate_per_minute"] = round(blink_rate, 2)
                    
                    if elapsed_time > 20: 
                        if blink_rate > CVS_UPPER_LIMIT: 
                            self.state["is_fatigued"] = False
                            self.state["message"] = "Normal (>17 kedip/mnt)"
                        elif CVS_LOWER_LIMIT <= blink_rate <= CVS_UPPER_LIMIT: 
                            self.state["is_fatigued"] = True
                            self.state["message"] = "Astenopia/CVS (<9 kedip/mnt)"
                        else:
                            self.state["is_fatigued"] = True
                            self.state["message"] = "CVS Parah/Mata Kering (<9 kedip/mnt)"
                    else:
                        self.state["message"] = f"Kalibrasi Rate ({int(elapsed_time)}/20s)..."

                    if self.state["is_drowsy"]:
                        self.state["message"] = "PERINGATAN: PENGGUNA MENGANTUK!"
        return self.state, frame

# API GET HTTP untuk mengecek status (Debugging)
@app.get("/api/status")
def api_status():
    return {"status": "Backend Aktif dan Tersedia", "message": "Gunakan websocket di endpoint ws://localhost:8000/ws/detect untuk data realtime kamera."}

# === Endpoint WebSocket untuk Terhubung dengan Website ===
@app.websocket("/ws/detect")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Website Backend Terhubung via WebSocket!")
    
    detector = FatigueDetector()
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5)
    
    try:
        while True:
            # Terima frame Base64 dari format Data URL frontend
            data = await websocket.receive_text()
            
            # Jika mendapat pesan restore kalibrasi dari frontend
            if data.startswith("restore_calibration"):
                if ":" in data:
                    try:
                        detector.focal_length = float(data.split(":")[1])
                        detector.state["focal_length"] = detector.focal_length
                    except ValueError:
                        pass
                detector.state["is_calibrated"] = True
                await websocket.send_json({"calibrating": False, "is_calibrated": True})
                continue

            # Jika mendapat pesan kalibrasi
            if data == "calibrate":
                detector.calibrate_requested = True
                await websocket.send_json({"calibrating": True})
                continue
                
            header, encoded = data.split(",", 1) if "," in data else ("", data)
            
            if not encoded:
                continue

            # Tambahkan padding jika kurang
            encoded += "=" * ((4 - len(encoded) % 4) % 4)

            # Konversi Base64 jadi numpy array dan decode pakai OpenCV
            try:
                img_bytes = base64.b64decode(encoded)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                print("Error decoding frame:", e)
                continue
            
            # Jika frame berhasil dibuat
            if frame is not None:
                # Proses frame untuk hitung EAR (tambah model/logika lain nanti spt Distance)
                state, processed_frame = detector.process_frame(frame, face_mesh)
                
                # --- TAMBAHAN DEBUGGING (cv2.imshow) ---
                # Gambarkan informasi EAR & Alert di layar agar bisa dibandingkan dengan data di website
                cv2.putText(processed_frame, f"EAR: {state['current_ear']} (Thresh: {state['dynamic_threshold']})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(processed_frame, f"Blinks/min: {state['blink_rate_per_minute']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(processed_frame, f"State: {state['message']}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Masukkan frame secara asynchronous ke display_queue tanpa block event loop
                if display_queue.full():
                    try:
                        display_queue.get_nowait() # Buang frame usang jika tertunda
                    except queue.Empty:
                        pass
                try:
                    display_queue.put_nowait(processed_frame)
                except queue.Full:
                    pass
                # ---------------------------------------

                # Kirim state kembali ke web
                await websocket.send_json(state)
                
    except WebSocketDisconnect:
        print("Koneksi ditutup oleh Web Frontend")
    finally:
        face_mesh.close()
        # Saat websocket putus, hilangkan window debugging tanpa mematikan thread
        if not display_queue.full():
            display_queue.put("CLOSE")
        else:
            try:
                display_queue.get_nowait()
                display_queue.put_nowait("CLOSE")
            except:
                pass
        # cv2.destroyAllWindows() jangan dipanggil langsung di sini karena beda thread


def run_api():
    """Jalankan server FastAPI"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_api()
