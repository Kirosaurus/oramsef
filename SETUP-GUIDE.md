# 🪟 Panduan Setup Windows - FESMARO

Panduan ini membantu Anda menginstal dan menjalankan FESMARO di Windows, termasuk solusi untuk error umum seperti:
> `No Python in C:\Users\...\WindowsApps\PythonSoftwareFoundation.Python.3.10_...`

---

## ✅ Langkah 1: Instal Python (dari situs resmi, BUKAN Windows Store)

Error di atas muncul karena Python yang terdeteksi berasal dari **Windows Store**, yang seringkali tidak berfungsi dengan baik untuk proyek Python.

### Cara instal Python yang benar:

1. Buka browser dan kunjungi: **https://www.python.org/downloads/**
2. Klik tombol **"Download Python 3.10.x"** (atau versi 3.8–3.11)
3. Jalankan file installer yang telah diunduh
4. ⚠️ **PENTING**: Centang opsi **"Add Python to PATH"** sebelum klik Install Now

   ![Centang Add Python to PATH](https://docs.python.org/3/_images/win_installer.png)

5. Klik **"Install Now"**
6. Setelah selesai, klik **"Disable path length limit"** jika muncul opsi tersebut

### Verifikasi instalasi:

Buka **Command Prompt** (CMD) baru dan ketik:
```cmd
python --version
```
Seharusnya muncul: `Python 3.10.x` (atau versi yang Anda instal)

---

## ✅ Langkah 2: Clone / Download Repository

Jika belum punya repository-nya, clone dengan Git:
```cmd
git clone https://github.com/Kirosaurus/oramsef.git
cd oramsef
```

Atau unduh sebagai ZIP dari GitHub lalu ekstrak ke folder pilihan Anda.

---

## ✅ Langkah 3: Buat Virtual Environment

Buka **Command Prompt** atau **PowerShell** di dalam folder proyek:

```cmd
python -m venv .venv
```

Aktifkan virtual environment:

- **Command Prompt (CMD)**:
  ```cmd
  .venv\Scripts\activate
  ```
- **PowerShell**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  > Jika PowerShell menolak karena policy, jalankan dulu:
  > ```powershell
  > Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  > ```

Setelah berhasil, prompt Anda akan berubah menjadi: `(.venv) C:\...>`

---

## ✅ Langkah 4: Instal Dependencies

Dengan virtual environment aktif, jalankan:

```cmd
pip install -r requirements.txt
```

Tunggu hingga semua paket selesai terinstal (opencv-python, mediapipe, numpy, fastapi, uvicorn, websockets).

---

## ✅ Langkah 5: Jalankan Aplikasi

### Jalankan Backend (Server AI):
```cmd
python Module/modulEAR.py
```
Tunggu hingga muncul pesan: `Uvicorn running on http://0.0.0.0:8000`

### Jalankan Frontend (Web Interface):

**Opsi A - VS Code Live Server (Disarankan):**
- Instal ekstensi **Live Server** di VS Code
- Klik kanan `Website/index.html` → pilih **"Open with Live Server"**

**Opsi B - Python HTTP Server:**
```cmd
cd Website
python -m http.server 5500
```
Buka browser ke: **http://localhost:5500**

---

## 🔧 Troubleshooting

### ❌ Error: `No Python in C:\Users\...\WindowsApps\...`

**Penyebab:** Python terinstal dari Windows Store, bukan dari python.org

**Solusi:**
1. Uninstal Python dari Windows Store (Settings → Apps → cari Python → Uninstall)
2. Instal ulang dari **https://www.python.org/downloads/** dengan centang **"Add Python to PATH"**
3. Buka CMD baru dan coba lagi

---

### ❌ Error: `python` tidak dikenali sebagai perintah

**Penyebab:** Python tidak ditambahkan ke PATH saat instalasi

**Solusi:**
1. Cari **"Environment Variables"** di Windows Search
2. Klik **"Edit the system environment variables"**
3. Klik **"Environment Variables..."**
4. Di bagian **"System variables"**, klik **Path** lalu **Edit**
5. Tambahkan path ke folder Python Anda, misalnya:
   - `C:\Python310\`
   - `C:\Python310\Scripts\`
6. Klik OK dan buka CMD baru

Alternatif lebih mudah: Uninstal dan instal ulang Python, kali ini dengan mencentang **"Add Python to PATH"**.

---

### ❌ Error: `pip install` gagal / timeout

**Solusi:**
```cmd
pip install -r requirements.txt --timeout 120
```

---

### ❌ Error saat mengaktifkan `.venv` di PowerShell

```
.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Solusi:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Lalu coba aktifkan kembali.

---

### ❌ Error: `ModuleNotFoundError` saat menjalankan `modulEAR.py`

**Penyebab:** Virtual environment tidak aktif atau dependencies belum terinstal

**Solusi:**
1. Pastikan virtual environment aktif (ada `(.venv)` di awal prompt)
2. Jalankan ulang: `pip install -r requirements.txt`

---

### ❌ Kamera tidak terdeteksi / error OpenCV

**Solusi:**
- Pastikan tidak ada aplikasi lain yang menggunakan kamera (Zoom, Teams, dll.)
- Coba restart CMD dan jalankan ulang backend

---

## 💡 Tips

- Gunakan **Python 3.10** untuk kompatibilitas terbaik dengan MediaPipe
- Selalu aktifkan virtual environment sebelum menjalankan aplikasi
- Jika menggunakan VS Code, instal ekstensi **Python** dari Microsoft untuk kemudahan pengembangan
