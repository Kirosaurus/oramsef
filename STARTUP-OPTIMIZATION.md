# ⏱️ Panduan Startup & Optimasi Performa FESMARO

Dokumen ini menjelaskan mengapa proses pertama kali (`first run`) aplikasi FESMARO bisa terasa lambat dan memakan banyak RAM, serta cara mengatasinya.

---

## 🤔 Mengapa First Run Sangat Lama?

Saat pertama kali menjalankan `python Module/modulEAR.py`, aplikasi perlu melakukan beberapa hal sebelum server siap:

### 1. Inisialisasi MediaPipe Face Mesh (Penyebab Utama) 📦

Di dalam `modulEAR.py`, model Face Mesh dari MediaPipe diinisialisasi setiap kali ada koneksi WebSocket masuk:

```python
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
```

Proses ini membutuhkan waktu karena:
- MediaPipe harus **memuat model neural network** ke dalam memori (~50–100 MB model files)
- Model ini memerlukan **alokasi buffer RAM** yang besar untuk inferensi real-time
- Pada first run, sistem melakukan **caching model** ke disk untuk akses lebih cepat berikutnya

### 2. Startup FastAPI + Uvicorn 🚀

Server Uvicorn perlu menginisialisasi:
- FastAPI application dan middleware CORS
- Threading untuk display queue (OpenCV debugging window)
- Semua modul Python yang diimport (`cv2`, `mediapipe`, `numpy`, dll.)

### 3. Import Library Besar

Saat Python memuat semua library:
- `opencv-python` (cv2): ~50–150 MB
- `mediapipe`: ~200–400 MB
- `numpy`, `fastapi`, `uvicorn`: ~50–100 MB

---

## 💾 Mengapa RAM Usage Bisa 3–4 GB?

Ini adalah perilaku **normal** dari MediaPipe. Berikut estimasi penggunaan memori:

| Komponen | Estimasi RAM |
|---|---|
| MediaPipe Face Mesh model | 2–3 GB |
| FastAPI + Uvicorn server | 300–500 MB |
| OpenCV + buffer frame | 200–400 MB |
| Python interpreter + NumPy | 100–200 MB |
| **Total** | **~3–4 GB** |

> **Catatan:** Penggunaan RAM yang tinggi ini adalah trade-off untuk mendapatkan performa deteksi real-time yang akurat. MediaPipe mengalokasikan buffer besar di memori agar bisa memproses setiap frame dengan latensi rendah.

---

## ⏳ Berapa Lama Waktu Tunggu?

Estimasi waktu startup berdasarkan spesifikasi hardware:

| Spesifikasi | Estimasi Waktu |
|---|---|
| RAM 16 GB+ / SSD NVMe / CPU modern | 10–30 detik |
| RAM 8 GB / SSD SATA / CPU mid-range | 30–60 detik |
| RAM 4–8 GB / HDD / CPU lama | 60–120 detik |
| RAM < 4 GB | ⚠️ Kemungkinan crash atau sangat lambat |

---

## ✅ Tanda-Tanda Aplikasi Sudah Siap

Tunggu hingga muncul pesan berikut di terminal:

```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Jangan menutup terminal atau mengira aplikasi frozen sebelum pesan ini muncul!**

---

## 🔁 Second Run Jauh Lebih Cepat

Setelah first run selesai:
- Model MediaPipe sudah ter-cache di disk
- Library Python sudah ter-cache oleh OS
- Second run biasanya **50–70% lebih cepat** dari first run

---

## 🛠️ Tips Mengurangi Memory Usage

### Opsi 1: Nonaktifkan `refine_landmarks`

Di file `Module/modulEAR.py`, ubah parameter ini:

```python
# Sebelum (menggunakan lebih banyak RAM):
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,   # <-- ubah ini
    ...
)

# Sesudah (lebih hemat RAM, akurasi sedikit berkurang):
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=False,  # <-- menjadi False
    ...
)
```

> ⚠️ Peringatan: Menonaktifkan `refine_landmarks` akan mengurangi akurasi deteksi iris dan landmark di sekitar mata, yang bisa mempengaruhi akurasi perhitungan EAR.

### Opsi 2: Tutup Aplikasi Lain

Tutup aplikasi yang memakan banyak RAM seperti:
- Browser dengan banyak tab
- IDE berat (VS Code dengan banyak extension aktif)
- Aplikasi video/streaming

### Opsi 3: Gunakan Python 64-bit

Pastikan Python yang digunakan adalah **versi 64-bit** agar bisa mengakses RAM lebih dari 4 GB:

```bash
python -c "import struct; print('64-bit' if struct.calcsize('P') * 8 == 64 else '32-bit')"
```

---

## 🎮 Akselerasi GPU (Opsional)

MediaPipe secara default menggunakan CPU. Jika ingin mencoba akselerasi:

### Cek apakah GPU tersedia:

```bash
python -c "import cv2; print(cv2.cuda.getCudaEnabledDeviceCount())"
```

> **Catatan:** MediaPipe versi Python saat ini (0.10.x) memiliki dukungan GPU terbatas di platform tertentu. Akselerasi GPU lebih optimal pada implementasi C++ atau Android/iOS.

---

## 🔍 Monitoring Startup Real-Time

Untuk memantau proses startup secara real-time, gunakan script yang disediakan:

```bash
# Di terminal terpisah, sebelum menjalankan backend:
python startup_monitor.py
```

Script ini akan menampilkan penggunaan CPU dan RAM secara live selama proses startup berlangsung.

Lihat contoh output di file `startup_progress.txt`.

---

## 🚨 Troubleshooting

### Aplikasi crash saat startup (MemoryError)

**Penyebab:** RAM tidak cukup (biasanya < 4 GB tersedia)

**Solusi:**
1. Tutup semua aplikasi lain untuk membebaskan RAM
2. Tambah virtual memory (swap) di Windows:
   - Buka **System Properties** → **Advanced** → **Performance Settings** → **Advanced** → **Virtual memory**
   - Set ke minimal 4096 MB
3. Upgrade RAM jika memungkinkan (minimal 8 GB disarankan)

### MediaPipe gagal inisialisasi

**Pesan error:** `Could not find model file` atau `Failed to load model`

**Solusi:**
```bash
# Reinstall MediaPipe untuk memastikan model file lengkap:
pip uninstall mediapipe -y
pip install mediapipe
```

### Python import error saat startup

**Pesan error:** `ModuleNotFoundError: No module named 'cv2'` (atau modul lain)

**Solusi:**
```bash
# Pastikan virtual environment aktif:
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# Reinstall semua dependencies:
pip install -r requirements.txt
```

---

## 📊 Alur Startup Normal

```
[1] python Module/modulEAR.py
       │
       ▼
[2] Import library (cv2, mediapipe, numpy, fastapi...)
    └─ Waktu: 5–15 detik
       │
       ▼
[3] Inisialisasi FastAPI + CORS middleware
    └─ Waktu: 1–3 detik
       │
       ▼
[4] Threading display_queue dimulai
    └─ Waktu: < 1 detik
       │
       ▼
[5] Uvicorn server berjalan di port 8000 ✅
    └─ Server siap menerima koneksi WebSocket
       │
       ▼
[6] WebSocket pertama terhubung dari frontend
       │
       ▼
[7] MediaPipe Face Mesh diinisialisasi
    └─ Waktu: 20–60 detik, RAM: 2–3 GB digunakan
       │
       ▼
[8] Sistem siap mendeteksi wajah dan mata ✅
```

---

*Untuk panduan instalasi lengkap, lihat [README.md](README.md)*
