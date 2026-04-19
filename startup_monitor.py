"""
startup_monitor.py - FESMARO Startup Performance Monitor

Skrip ini memantau penggunaan CPU dan RAM secara real-time selama proses
startup modulEAR.py berlangsung. Jalankan di terminal terpisah sebelum
atau bersamaan dengan menjalankan backend.

Cara pakai:
    Terminal 1: python startup_monitor.py
    Terminal 2: python Module/modulEAR.py

Tekan Ctrl+C untuk menghentikan monitoring.
"""

import sys
import time
import os

try:
    import psutil
except ImportError:
    print("=" * 60)
    print("ERROR: Library 'psutil' tidak ditemukan.")
    print("Instal dengan perintah: pip install psutil")
    print("=" * 60)
    sys.exit(1)

# --- Konfigurasi ---
REFRESH_INTERVAL = 1.0          # Interval pembaruan tampilan (detik)
BACKEND_PROCESS_KEYWORDS = [    # Kata kunci untuk mendeteksi proses backend
    "modulEAR",
    "uvicorn",
    "Module/modulEAR",
    "Module\\modulEAR",
]
MEDIAPIPE_READY_PORT = 8000     # Port yang dipakai Uvicorn


def format_bytes(size_bytes):
    """Konversi bytes ke format yang mudah dibaca (MB/GB)."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.1f} GB"
    return f"{size_bytes / (1024 ** 2):.0f} MB"


def make_progress_bar(value, max_value, width=25, char_filled="█", char_empty="░"):
    """Buat progress bar teks."""
    ratio = min(value / max_value, 1.0) if max_value > 0 else 0
    filled = int(ratio * width)
    bar = char_filled * filled + char_empty * (width - filled)
    return f"[{bar}]"


def check_server_ready():
    """Cek apakah Uvicorn sudah berjalan di port yang ditentukan."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", MEDIAPIPE_READY_PORT), timeout=0.5):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def find_backend_processes():
    """Cari proses Python yang menjalankan backend FESMARO."""
    backend_procs = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "status"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(kw in cmdline for kw in BACKEND_PROCESS_KEYWORDS):
                backend_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return backend_procs


def get_system_stats():
    """Ambil statistik sistem saat ini."""
    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    return {
        "cpu_percent": cpu_percent,
        "ram_used": mem.used,
        "ram_total": mem.total,
        "ram_percent": mem.percent,
        "ram_available": mem.available,
    }


def get_process_stats(proc):
    """Ambil statistik untuk satu proses."""
    try:
        with proc.oneshot():
            mem_info = proc.memory_info()
            cpu = proc.cpu_percent(interval=None)
            status = proc.status()
        return {
            "pid": proc.pid,
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "cpu": cpu,
            "status": status,
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def clear_terminal():
    """Bersihkan layar terminal."""
    os.system("cls" if os.name == "nt" else "clear")


def run_monitor():
    """Loop utama monitoring."""
    start_time = time.time()
    server_was_ready = False
    peak_ram_system = 0
    peak_ram_process = 0

    # Inisialisasi cpu_percent agar pembacaan pertama tidak 0
    psutil.cpu_percent(interval=None)

    print("🚀 FESMARO Startup Monitor")
    print("   Menunggu proses backend berjalan...")
    print("   (Jalankan: python Module/modulEAR.py di terminal lain)\n")
    print("   Tekan Ctrl+C untuk keluar.\n")
    time.sleep(REFRESH_INTERVAL)

    try:
        while True:
            elapsed = time.time() - start_time
            stats = get_system_stats()
            backend_procs = find_backend_processes()
            server_ready = check_server_ready()

            # Update peak values
            if stats["ram_used"] > peak_ram_system:
                peak_ram_system = stats["ram_used"]

            # Tampilkan header
            clear_terminal()
            print("╔══════════════════════════════════════════════════════════╗")
            print("║           🚀 FESMARO Startup Monitor                    ║")
            print("╠══════════════════════════════════════════════════════════╣")

            # Status server
            if server_ready:
                if not server_was_ready:
                    server_was_ready = True
                status_line = "✅ Server AKTIF  (ws://localhost:8000/ws/detect)"
            else:
                status_line = "⏳ Menunggu server siap di port 8000..."
            print(f"║  Status : {status_line:<50}║")
            print(f"║  Waktu  : {elapsed:>6.1f} detik sejak monitor dimulai          ║")
            print("╠══════════════════════════════════════════════════════════╣")

            # Statistik sistem
            print("║  📊 Statistik Sistem                                    ║")
            cpu_bar = make_progress_bar(stats["cpu_percent"], 100, width=20)
            print(f"║  CPU    : {cpu_bar}  {stats['cpu_percent']:>5.1f}%          ║")
            ram_bar = make_progress_bar(stats["ram_percent"], 100, width=20)
            ram_info = f"{format_bytes(stats['ram_used'])} / {format_bytes(stats['ram_total'])}"
            print(f"║  RAM    : {ram_bar}  {stats['ram_percent']:>5.1f}%          ║")
            print(f"║  RAM    : {ram_info:<50}║")
            print(f"║  Tersedia: {format_bytes(stats['ram_available']):<49}║")
            print(f"║  RAM Peak: {format_bytes(peak_ram_system):<48}║")

            print("╠══════════════════════════════════════════════════════════╣")

            # Proses backend
            proc_count = len(backend_procs)
            if backend_procs:
                proc_label = f"🐍 Proses Backend Terdeteksi ({proc_count} proses)"
                print(f"║  {proc_label:<56}║")
                for proc in backend_procs:
                    pstats = get_process_stats(proc)
                    if pstats is None:
                        continue
                    if pstats["rss"] > peak_ram_process:
                        peak_ram_process = pstats["rss"]
                    status_icon = "🟢" if pstats["status"] == "running" else "🟡"
                    print(f"║  {status_icon} PID {pstats['pid']:<6} | "
                          f"CPU: {pstats['cpu']:>5.1f}% | "
                          f"RAM: {format_bytes(pstats['rss']):<10}║")
                if peak_ram_process > 0:
                    print(f"║  RAM Backend Peak : {format_bytes(peak_ram_process):<40}║")
            else:
                print("║  🔍 Proses backend belum terdeteksi.                    ║")
                print("║     Jalankan: python Module/modulEAR.py                 ║")

            print("╠══════════════════════════════════════════════════════════╣")

            # Panduan tahapan startup
            print("║  📋 Tahapan Startup (estimasi)                          ║")
            libs_imported = bool(backend_procs)
            stages = [
                ("Import library (cv2, mediapipe, numpy...)", libs_imported),
                ("FastAPI + Uvicorn mulai berjalan", server_ready),
                ("WebSocket endpoint siap", server_ready),
                ("MediaPipe Face Mesh dimuat saat koneksi pertama", False),
            ]
            for label, done in stages:
                icon = "✅" if done else "⬜"
                print(f"║  {icon} {label:<54}║")

            print("╠══════════════════════════════════════════════════════════╣")

            # Pesan panduan
            if server_ready:
                print("║  ✅ Backend siap! Buka Website/index.html di browser.   ║")
                print("║     Saat koneksi WebSocket pertama, MediaPipe akan      ║")
                print("║     dimuat (~20–60 detik, RAM naik 2–3 GB).             ║")
            elif elapsed < 30:
                print("║  ⏳ Harap tunggu... Proses startup sedang berlangsung.  ║")
                print("║     Ini NORMAL, terutama pada first run.                ║")
            elif elapsed < 90:
                print("║  ⏳ Startup memakan waktu lebih lama (hardware lambat). ║")
                print("║     Jika error muncul di terminal backend, cek README.  ║")
            else:
                print("║  ⚠️  Startup sangat lama. Cek terminal backend untuk    ║")
                print("║     melihat apakah ada error atau aplikasi frozen.      ║")

            print("╚══════════════════════════════════════════════════════════╝")
            print("  Tekan Ctrl+C untuk menghentikan monitor.")

            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n✋ Monitor dihentikan.")
        elapsed = time.time() - start_time
        print(f"\n📈 Ringkasan Session:")
        print(f"   Durasi monitor  : {elapsed:.1f} detik")
        print(f"   Peak RAM sistem : {format_bytes(peak_ram_system)}")
        if peak_ram_process > 0:
            print(f"   Peak RAM backend: {format_bytes(peak_ram_process)}")
        if server_was_ready:
            print("   Status akhir    : ✅ Server berhasil berjalan")
        else:
            print("   Status akhir    : ❌ Server belum sempat berjalan")
        print()


if __name__ == "__main__":
    run_monitor()
