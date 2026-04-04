# FESMARO: Deteksi Kesehatan Mata & Jarak Layar

Sistem pendeteksi kesehatan mata berbasis AI secara *real-time* yang memberikan peringatan kelelahan mata (Computer Vision Syndrome), posisi layar yang terlalu dekat, dan membantu menerapkan **aturan 20-20-20** demi menjaga kesehatan penglihatan di era digital.

Sistem ini terbagi menjadi dua bagian:
1. **Backend (Python)**: Menggunakan MediaPipe Face Mesh untuk kalkulasi *Eye Aspect Ratio (EAR)*, perkiraan jarak (*distance estimation*), dan frekuensi kedipan melalui *WebSocket*.
2. **Frontend (HTML/CSS/JS)**: Antarmuka *Progressive Web App (PWA)* interaktif yang menangani jalannya kamera, memberikan *pop-up* peringatan, dan notifikasi UI/Sistem Operasi.

---

## 🛠️ Prasyarat (Prerequisites)
Sebelum menjalankan program, pastikan Anda telah menginstal:
- **Python 3.8 - 3.11** (MediaPipe sangat disarankan berjalan stabil di rentang versi ini).
- Webcam / Kamera fungsional
- Browser Modern (Chrome, Edge, atau Firefox)

---

## 📦 Panduan Instalasi (Setup)

### 1. Buat Virtual Environment (Opsional namun disarankan)
Buka terminal/CMD di dalam folder proyek ini lalu jalankan:
```bash
python -m venv .venv
```
Aktifkan Virtual Environment:
- **Windows**: `.venv\Scripts\activate` atau `.\.venv\Scripts\Activate.ps1`
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
- **`WARNING: failed to connect to WebSocket`**: Pastikan server backend `modulEAR.py` Anda sudah berjalan. Periksa apakah ada error Python di terminal backend.
- **Notifikasi Desktop tidak muncul**: Izinkan (Allow) *Notifications* di ujung *URL/Address bar* *browser* Anda saat layar awal meminta izin.
- **Kamera tidak mau terbuka**: Pastikan Anda belum menggunakan kamera di Tab, Google Meet, Zoom, atau aplikasi lain karena kamera hanya bisa dipakai oleh satu program dalam satu waktu.

---

## ⏱️ Performa Startup & Penggunaan RAM

### First Run Lambat (30–120 Detik) — NORMAL!

Jika `python Module/modulEAR.py` terasa sangat lambat atau Task Manager menunjukkan **3–4 GB RAM** terpakai, ini adalah perilaku **normal**. Penyebabnya adalah inisialisasi model **MediaPipe Face Mesh** yang membutuhkan alokasi memori besar untuk inferensi real-time.

**Tanda aplikasi sudah siap** — tunggu hingga muncul pesan ini di terminal:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Second run akan jauh lebih cepat** karena model sudah ter-*cache*.

### Monitoring Real-Time Saat Startup

Untuk memantau proses startup secara live (CPU, RAM, status server):

```bash
# Instal dependensi monitoring (satu kali):
pip install psutil

# Jalankan monitor di terminal terpisah:
python startup_monitor.py
```

Lihat file `startup_progress.txt` untuk contoh tampilan output monitor.

### Panduan Lengkap Optimasi Startup

Untuk penjelasan mendalam tentang:
- Mengapa RAM bisa 3–4 GB
- Cara mengurangi penggunaan memori
- Tips akselerasi GPU
- Troubleshooting crash saat startup

👉 Baca **[STARTUP-OPTIMIZATION.md](STARTUP-OPTIMIZATION.md)**
