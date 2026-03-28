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
import webbrowser
import asyncio

# --- Fix untuk PyInstaller --windowed (menghindari error sys.stdout NoneType) ---
if sys.stdout is None or sys.stderr is None:
    class DummyWriter:
        def write(self, *args): pass
        def flush(self, *args): pass
        def isatty(self): return False
    
    if sys.stdout is None: sys.stdout = DummyWriter()
    if sys.stderr is None: sys.stderr = DummyWriter()
# -----------------------------------------------------------------------------

# Deteksi apakah berjalan sebagai script biasa atau .exe dari PyInstaller
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    # Naik satu folder dari direktori tempat modulEAR.py berada
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Menambahkan direktori Module ke sys.path untuk import modulDist
sys.path.append(os.path.join(base_path, "Module"))
import modulDist

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# === Sistem Auto-Shutdown Graceful ===
keepalive_clients = 0
active_clients = 0
shutdown_timer = None
startup_timer = None
server_instance = None

def do_shutdown():
    print("Tab ditutup. Mematikan aplikasi...")
    os._exit(0)

def schedule_shutdown(delay=10.0):
    global shutdown_timer, keepalive_clients
    # Jangan matikan program jika web masih terhubung ke sensor aktif atau ada tab aktif lain!
    if keepalive_clients > 0 or active_clients > 0:
        return
        
    cancel_shutdown()
    # Memberikan toleransi cukup panjang 10 detik. Saat minimize kadang Chrome mereset Network Stack sesaat. 
    # Selama interval 10 detik ini script JS (jika browser tidak mati) akan melakukan auto-reconnect,
    # yang kemudian di-handle oleh cancel_shutdown() di endpoint keepalive.
    shutdown_timer = threading.Timer(delay, do_shutdown)
    shutdown_timer.start()

def cancel_shutdown():
    global shutdown_timer
    if shutdown_timer:
        shutdown_timer.cancel()
        shutdown_timer = None

def cancel_startup():
    global startup_timer
    if startup_timer:
        startup_timer.cancel()
        startup_timer = None

# Timer awal saat app baru dijalankan, beri waktu 60 detik agar browser sempat loading.
startup_timer = threading.Timer(60.0, do_shutdown)
startup_timer.start()
# =====================================

# Inisialisasi FastAPI
app = FastAPI(title="Eye Fatigue Detection API")

# API Keep-Alive via WebSocket (Handal melawan efek Minimize Tab)
@app.websocket("/ws/keepalive")
async def keepalive_ws(websocket: WebSocket):
    global keepalive_clients
    await websocket.accept()
    keepalive_clients += 1
    cancel_startup()
    cancel_shutdown()
    try:
        # Menunggu sampai browser benar-benar ditutup
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        keepalive_clients -= 1
        if keepalive_clients <= 0 and active_clients <= 0:
            print("Koneksi terputus. Menunggu 10 detik memastikan bukan Minimize Socket Reset...")
            schedule_shutdown(10.0)

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
        self.camera_cap = None
        self.is_running = False
        
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
            "focal_length": 0.0,
            "frame_base64": "" # Menambahkan state agar website juga bisa ambil frame video
        }
        self.calibrate_requested = False
        self.focal_length = 0.0
        self.KNOWN_WIDTH = 6.3 # Estimasi ICD (Inner Canthal Distance) rata-rata manusia
        self.KNOWN_DISTANCE = 60.0 # Asumsi estimasi jarak lengan saat kalibrasi

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
    global active_clients
    await websocket.accept()
    active_clients += 1
    cancel_shutdown() # Konek, batalkan timer shutdown (jika ada)
    print("Website Backend Terhubung via WebSocket!")
    
    detector = FatigueDetector()
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5)

    # Inisialisasi Kamera di Background Python
    detector.camera_cap = cv2.VideoCapture(0)
    
    # Tunggu sebentar jika kamera masih dikunci (locked) oleh proses web disconnect sebelumnya (biasanya karena cepatnya klik tombol Start setelah Reset)
    retry_time = 0
    while not detector.camera_cap.isOpened() and retry_time < 30:
        await asyncio.sleep(0.1)
        detector.camera_cap.open(0)
        retry_time += 1
        
    detector.camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    detector.camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    detector.is_running = True

    # Pindahkan proses baca koneksi menjadi async task (hanya untuk terima config sesekali)
    async def receive_messages():
        try:
            while detector.is_running:
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
                
                # Jika mendapat pesan kalibrasi
                elif data == "calibrate":
                    detector.calibrate_requested = True
                    await websocket.send_json({"calibrating": True})
        except WebSocketDisconnect:
            detector.is_running = False
        except Exception:
            pass
            
    # Jalankan penerima pesan di background
    recv_task = asyncio.create_task(receive_messages())
    
    empty_frame_count = 0

    try:
        # Loop utama dari Python (akan jalan sekencang cv2 frame rate tanpa peduli web lag)
        while detector.is_running:
            ret, frame = detector.camera_cap.read()
            if not ret or frame is None:
                empty_frame_count += 1
                if empty_frame_count > 50: # Jika 50 frame berturut-turut gagal (Kamera nyangkut)
                    print("Kamera gagal membaca frame berulang kali, mencoba restart kamera internal...")
                    detector.camera_cap.release()
                    await asyncio.sleep(0.5)
                    detector.camera_cap = cv2.VideoCapture(0)
                    detector.camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    detector.camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    empty_frame_count = 0
                await asyncio.sleep(0.01)
                continue
            
            empty_frame_count = 0
                
            # Proses frame untuk hitung EAR (tambah model/logika lain nanti spt Distance)
            state, processed_frame = detector.process_frame(frame, face_mesh)
            
            # --- TAMBAHAN DEBUGGING (cv2.imshow) ---
            cv2.putText(processed_frame, f"EAR: {state['current_ear']} (Thresh: {state['dynamic_threshold']})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(processed_frame, f"Blinks/min: {state['blink_rate_per_minute']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(processed_frame, f"State: {state['message']}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            if display_queue.full():
                try: display_queue.get_nowait()
                except queue.Empty: pass
            try: display_queue.put_nowait(processed_frame)
            except queue.Full: pass
            # ---------------------------------------

            # Convert frame kembali ke bas64 agar video tetap tampil di web Frontend
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            state["frame_base64"] = f"data:image/jpeg;base64,{frame_base64}"

            # Kirim state (+ gambar) kembali ke web
            try:
                await websocket.send_json(state)
            except Exception:
                break # terputus
                
            # Beri sedikit delay agar async runtime berjalan mulus
            await asyncio.sleep(0.03) 
                
    except Exception as e:
        print("Koneksi Error/Ditutup:", e)
    finally:
        # Bersihkan resource saat UI disconnect
        detector.is_running = False
        recv_task.cancel()
        if detector.camera_cap:
            detector.camera_cap.release()
        
        active_clients -= 1
        if active_clients <= 0:
            schedule_shutdown(5.0) # Tunggu 5 detik sebelum mematikan server
        
        face_mesh.close()
        if not display_queue.full():
            display_queue.put("CLOSE")
        else:
            try:
                display_queue.get_nowait()
                display_queue.put_nowait("CLOSE")
            except:
                pass


# === Mount Static Files Website dan Auto-Open Browser ===
website_dir = os.path.join(base_path, "Website")

class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, req_headers) -> bool:
        return False
        
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

app.mount("/", NoCacheStaticFiles(directory=website_dir, html=True), name="website")

def open_browser():
    """Tunggu beberapa detik agar server siap sebelum browser terbuka"""
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

def run_api():
    """Jalankan server FastAPI"""
    global server_instance
    threading.Thread(target=open_browser, daemon=True).start()
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server_instance = uvicorn.Server(config)
    server_instance.run()

if __name__ == "__main__":
    run_api()
