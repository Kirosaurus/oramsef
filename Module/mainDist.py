import cv2
import dlib
import math
import modulDist

# ----------------- KONFIGURASI -----------------
# Jarak aktual antara wajah dan layar saat proses kalibrasi (dalam centimeter)
KNOWN_DISTANCE = 50.0  

# Jarak nyata ICD (Inter-Canthal Distance) yaitu jarak antar sudut mata dalam (dalam centimeter). 
# Rata-rata orang dewasa adalah sekitar 3.2 cm. Anda bisa sesuaikan ini.
KNOWN_ICD = 3.2 

# Path file landmark. Pastikan kamu sudah mendownload dan menyimpan file ini di folder yang sama
PREDICTOR_PATH = "shape_predictor_68_face_landmarks.dat"
# -----------------------------------------------

# Inisialisasi dlib's face detector & facial landmark predictor
detector = dlib.get_frontal_face_detector()
try:
    predictor = dlib.shape_predictor(PREDICTOR_PATH)
except Exception as e:
    print(f"Error memuat predictor: {e}")
    print("Pastikan file 'shape_predictor_68_face_landmarks.dat' ada di direktori yang sama!")
    exit()

def get_icd_pixel_width(shape):
    # Untuk dlib 68-landmarks, poin mata bagian dalam adalah indeks 39 (mata kiri) dan 42 (mata kanan)
    pt_39 = (shape.part(39).x, shape.part(39).y) # Inner corner mata kiri
    pt_42 = (shape.part(42).x, shape.part(42).y) # Inner corner mata kanan
    
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
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Deteksi wajah di frame
        faces = detector(gray)
        
        for face in faces:
            # Dapatkan landmarks pada wajah
            shape = predictor(gray, face)
            
            # Hitung jarak ICD dalam hitungan piksel
            pixel_width, pt1, pt2 = get_icd_pixel_width(shape)
            
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
            if not calibrated and len(faces) > 0:
                focal_length = modulDist.calculate_focal_length(KNOWN_DISTANCE, KNOWN_ICD, pixel_width)
                calibrated = True
                print(f"[INFO] Kalibrasi selesai! Focal Length yang digunakan: {focal_length:.2f}")
            elif len(faces) == 0:
                print("[WARNING] Wajah tidak terdeteksi untuk kalibrasi. Coba lagi!")
                
        # Keluar jika tekan 'Q'
        if key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
