import cv2
import mediapipe as mp
import math
import modulDist

# ----------------- KONFIGURASI -----------------
# Jarak aktual antara wajah dan layar saat proses kalibrasi (dalam centimeter)
KNOWN_DISTANCE = 60.0  

# Jarak nyata ICD (Inter-Canthal Distance) yaitu jarak antar sudut mata dalam (dalam centimeter). 
# Rata-rata orang dewasa adalah sekitar 3.1 cm. Anda bisa sesuaikan ini.
KNOWN_ICD = 3.1
# -----------------------------------------------

# Inisialisasi MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def get_icd_pixel_width(face_landmarks, frame_width, frame_height):
    # Inner corner mata di MediaPipe: 133 (kiri), 362 (kanan)
    pt_left = face_landmarks.landmark[133]
    pt_right = face_landmarks.landmark[362]
    
    # Konversi ke koordinat piksel
    pt_39 = (int(pt_left.x * frame_width), int(pt_left.y * frame_height))
    pt_42 = (int(pt_right.x * frame_width), int(pt_right.y * frame_height))
    
    # Hitung jarak Euclidean (pixel) antara dua titik tersebut
    pixel_dist = math.hypot(pt_42[0] - pt_39[0], pt_42[1] - pt_39[1])
    return pixel_dist, pt_39, pt_42

def main():
    cap = cv2.VideoCapture(0)
    
    focal_length = None
    calibrated = False

    print("Tekan 'C' di keyboard saat posisimu pada jarak", KNOWN_DISTANCE, "cm untuk kalibrasi.")
    print("Tekan 'Q' untuk keluar program.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Flip frame agar tidak mirror (opsional)
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width, _ = frame.shape
        
        # Deteksi wajah di frame menggunakan MediaPipe
        results = face_mesh.process(rgb_frame)
        
        face_detected = False
        pixel_width = 0
        
        if results.multi_face_landmarks:
            face_detected = True
            for face_landmarks in results.multi_face_landmarks:
                # Hitung jarak ICD dalam hitungan piksel
                pixel_width, pt1, pt2 = get_icd_pixel_width(face_landmarks, frame_width, frame_height)
                
                # Visualisasi titik kalibrasi ICD di layar (warna hijau dan merah)
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
                cv2.circle(frame, pt1, 3, (0, 0, 255), -1)
                cv2.circle(frame, pt2, 3, (0, 0, 255), -1)
                
                if not calibrated:
                    # Pesan instruksi sebelum kalibrasi
                    cv2.putText(frame, f"Posisikan wajah {KNOWN_DISTANCE}cm dari layar.", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    cv2.putText(frame, "Lalu tekan 'C' untuk Kalibrasi.", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                else:
                    # Jika sudah kalibrasi, hitung jarak seketika menggunakan modulDist
                    distance = modulDist.distance_to_camera(focal_length, KNOWN_ICD, pixel_width)
                    
                    # Tampilkan hasil perhitungan jarak ke layar
                    cv2.putText(frame, f"Jarak: {distance:.2f} cm", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                
        cv2.imshow("Monitor Distance Detector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Logika tombol 'C' untuk menyimpan kalibrasi focal length
        if key == ord('c') or key == ord('C'):
            if not calibrated and face_detected:
                focal_length = modulDist.calculate_focal_length(KNOWN_DISTANCE, KNOWN_ICD, pixel_width)
                calibrated = True
                print(f"[INFO] Kalibrasi selesai! Focal Length yang digunakan: {focal_length:.2f}")
            elif not face_detected:
                print("[WARNING] Wajah tidak terdeteksi untuk kalibrasi. Coba lagi!")
                
        # Keluar jika tekan 'Q'
        if key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
