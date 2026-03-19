import cv2
import numpy as np
from scipy.spatial import distance as dist

def calculate_ear(eye_landmarks):
    # Jarak vertikal (p2-p6 dan p3-p5)
    v1 = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    v2 = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
    # Jarak horizontal (p1-p4)
    h = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
    
    # Rumus EAR sesuai literatur
    ear = (v1 + v2) / (2.0 * h) if h > 0 else 0
    return ear

# Load Haar Cascade untuk face
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Inisialisasi model Facemark LBF untuk 68 titik akurat
facemark = cv2.face.createFacemarkLBF()
try:
    facemark.loadModel("lbfmodel.yaml")
except cv2.error:
    print("Model lbfmodel.yaml belum didownload atau tidak ditemukan!")
    exit()

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    
    # Flip frame untuk efek cermin
    frame = cv2.flip(frame, 1)
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Deteksi wajah
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) > 0:
        # Deteksi 68 landmark wajah
        success, landmarks_list = facemark.fit(gray, faces)
        
        if success:
            for i, landmarks in enumerate(landmarks_list):
                # Landmarks berbentuk array float, ubah ke integer
                landmarks = landmarks[0].astype(int)
                
                # Pisahkan array landmark untuk Mata Kiri [36-41] dan Mata Kanan [42-47]
                left_eye_pts = landmarks[36:42]
                right_eye_pts = landmarks[42:48]
                
                # Hitung EAR (Eye Aspect Ratio)
                left_ear = calculate_ear(left_eye_pts)
                right_ear = calculate_ear(right_eye_pts)
                avg_ear = (left_ear + right_ear) / 2.0
                
                # Buat Polygon/Garis di sekeliling bentuk asli mata
                cv2.polylines(frame, [left_eye_pts], isClosed=True, color=(0, 255, 255), thickness=1)
                cv2.polylines(frame, [right_eye_pts], isClosed=True, color=(0, 255, 255), thickness=1)
                
                # Gambar titik landmark pada ujung mata
                for (x_lm, y_lm) in left_eye_pts:
                    cv2.circle(frame, (x_lm, y_lm), 2, (0, 255, 0), -1)
                for (x_lm, y_lm) in right_eye_pts:
                    cv2.circle(frame, (x_lm, y_lm), 2, (0, 255, 0), -1)
                
                # Threshold EAR: < 0.22 umumnya menandakan mata terpejam
                if avg_ear < 0.22:
                    cv2.putText(frame, "MATA TERTUTUP - KEDIP", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    cv2.putText(frame, f"EAR: {avg_ear:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # Draw face rectangle
                x, y, w, h = faces[i]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 1)

    # Display frame
    cv2.imshow('Facial Landmarks Detection', frame)
    
    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

