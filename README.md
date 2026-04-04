# FESMARO: Deteksi Kesehatan Mata & Jarak Layar

Sistem pendeteksi kesehatan mata berbasis AI secara *real-time* yang memberikan peringatan kelelahan mata (Computer Vision Syndrome), posisi layar yang terlalu dekat, dan membantu menerapkan **aturan 20-20-20** demi menjaga kesehatan penglihatan di era digital.

Sistem ini terbagi menjadi dua bagian:
1. **Backend (Python)**: Menggunakan MediaPipe Face Mesh untuk kalkulasi *Eye Aspect Ratio (EAR)*, perkiraan jarak (*distance estimation*), dan frekuensi kedipan melalui *WebSocket*.
2. **Frontend (HTML/CSS/JS)**: Antarmuka *Progressive Web App (PWA)* interaktif yang menangani jalannya kamera, memberikan *pop-up* peringatan, dan notifikasi UI/Sistem Operasi.

---

## 🛠️ Prasyarat (Prerequisites)
Sebelum menjalankan program, pastikan Anda telah menginstal:
- **Python 3.8 - 3.11** dari **[python.org](https://www.python.org/downloads/)** (bukan dari Windows Store). MediaPipe sangat disarankan berjalan stabil di rentang versi ini.
- Webcam / Kamera fungsional
- Browser Modern (Chrome, Edge, atau Firefox)

> **🪟 Pengguna Windows**: Jika Anda menemui error `No Python in C:\Users\...\WindowsApps\...`, baca **[SETUP-GUIDE.md](SETUP-GUIDE.md)** untuk panduan lengkap dan troubleshooting.

---

## 📦 Panduan Instalasi (Setup)

### 1. Buat Virtual Environment (Opsional namun disarankan)
Buka terminal/CMD di dalam folder proyek ini lalu jalankan:
```bash
python -m venv .venv
```
Aktifkan Virtual Environment:
- **Windows (CMD)**: `.venv\Scripts\activate`
- **Windows (PowerShell)**: `.\.venv\Scripts\Activate.ps1`
- **Mac/Linux**: `source .venv/bin/activate`

### 2. Instal Library/Modul yang Dibutuhkan
Instal semua *dependencies* menggunakan `pip` berdasarkan file `requirements.txt` yang telah disediakan:
```bash
pip install -r requirements.txt
```
*(Catatan: Ini akan menginstal opencv-python, mediapipe, numpy, fastapi, uvicorn, dan websockets).*

---

## 🚀 Cara Menjalankan Aplikasi (Run)

### 1. Menjalankan *Backend* (Server AI)
Sistem *frontend* butuh *backend* aktif untuk menganalisis wajah Anda dari video yang dikirim.
Posisikan terminal Anda di folder utama proyek (bukan di dalam Module/Website), lalu jalankan:
```bash
python Module/modulEAR.py
```
*Tunggu hingga muncul pesan bahwa Uvicorn berjalan di `0.0.0.0:8000`.*

### 2. Menjalankan *Frontend* (Antarmuka Web)
Berhubung antarmuka website ini menggunakan fitur *Desktop Notification* dan *Service Worker (PWA)*, **Anda harus menjalankannya melalui Local Web Server** (tidak bisa sekadar klik ganda file `.html`).

**Opsi A: Menggunakan ekstensi VS Code (Sangat Disarankan)**
- Instal ekstensi **Live Server** di VS Code.
- Klik kanan file `Website/index.html` dan pilih **"Open with Live Server"**.

**Opsi B: Menggunakan bawaan Python (Command Line)**
Buka terminal *baru* lagi, lalu masuk ke folder Website dan jalankan local server Python:
```bash
cd Website
python -m http.server 5500
```
Buka *browser* Anda dan kunjungi URL: **`http://localhost:5500`**

---

## ⚙️ Fitur Utama Aplikasi

- **Kalkulasi Jarak (*Distance Estimation*)**: Memberikan *feedback* bila wajah Anda berjarak kurang dari 46 cm dari layar (standar OSHA 46–61 cm).
- **Deteksi Frekuensi Kedip**: Menghitung *Blink per Minute*. Jika berada di bawah batas normal (9 kali/menit) selama 10 detik, akan memicu notifikasi desktop.
- **Deteksi Kantuk/Micro-sleep**: Mata terpejam lama mengirim *alert* kritis untuk segera istirahat.
- **Timer 20-20-20 Otomatis**: Setiap 20 menit bekerja di depan layar, sistem akan memaksa jeda layar selama 20 detik agar mata beralih dari fokus dekat.
- **Hard Stop (3 Jam)**: Mode perlindungan ekstrem jika terjadi kelelahan konstan (*fatigue*) setelah pemakaian menembus 3 jam nonstop.

## 🤝 Troubleshooting & Pesan Error Umum
- **`No Python in C:\Users\...\WindowsApps\...`**: Instal Python dari [python.org](https://www.python.org/downloads/) (bukan Windows Store) dengan mencentang **"Add Python to PATH"**. Lihat [SETUP-GUIDE.md](SETUP-GUIDE.md) untuk panduan lengkap.
- **`WARNING: failed to connect to WebSocket`**: Pastikan server backend `modulEAR.py` Anda sudah berjalan. Periksa apakah ada error Python di terminal backend.
- **Notifikasi Desktop tidak muncul**: Izinkan (Allow) *Notifications* di ujung *URL/Address bar* *browser* Anda saat layar awal meminta izin.
- **Kamera tidak mau terbuka**: Pastikan Anda belum menggunakan kamera di Tab, Google Meet, Zoom, atau aplikasi lain karena kamera hanya bisa dipakai oleh satu program dalam satu waktu.
