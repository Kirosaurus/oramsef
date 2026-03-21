// ═══════════════════════════════════════════
// INDEX PAGE — Scroll Reveal
// ═══════════════════════════════════════════

function initScrollReveal() {
  const reveals = document.querySelectorAll('.reveal');
  if (!reveals.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1 });

  reveals.forEach(el => observer.observe(el));
}

// ═══════════════════════════════════════════
// DETECTOR PAGE — Session & Biometric Logic
// ═══════════════════════════════════════════

// ─── STATE ────────────────────────────────────
let isActive = false;
let sessionSeconds = 0;
let timerSeconds = 20 * 60;
let totalBlinks = 0;
let totalAlertCount = 0;
let restSeconds = 20;
let isResting = false;
let isCalibrated = false;
let savedFocalLength = 0;

let isCurrentlyFatigued = false;
let isCurrentlyClose = false;
  let isCurrentlyLowBlink = false;
  let fatigueSeconds = 0;
  let closeSeconds = 0;
  let lowBlinkSeconds = 0;
let sessionInterval = null;
let timerInterval = null;
let dataInterval = null;
let restInterval = null;

// Simulated biometric data
const earData  = [0.28, 0.27, 0.26, 0.28, 0.29, 0.25, 0.24, 0.27, 0.28, 0.26];
const distData = [38, 42, 45, 40, 37, 50, 48, 43, 38, 35];
const blinkData = [15, 14, 13, 16, 15, 12, 13, 14, 15, 11];
let dataIdx = 0;

// ─── TOGGLE SESSION ───────────────────────────
function toggleSession() {
  if (!isActive) startSession();
  else stopSession();
}

function startSession() {
  isActive = true;

  // Meminta izin notifikasi jika belum
  if (window.Notification && Notification.permission !== 'granted') {
    Notification.requestPermission();
  }

  document.getElementById('startBtn').innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
    </svg>
    Akhiri Sesi`;
  document.getElementById('startBtn').classList.add('active');
  document.getElementById('camIdle').style.display = 'none';
  document.getElementById('camActive').style.display = 'block';
  document.getElementById('camBadge').textContent = 'LIVE';
  document.getElementById('camBadge').className = 'cam-badge live';
  document.getElementById('camRes').textContent = '1280 × 720';
  document.getElementById('navDot').className = 'status-dot live';
  document.getElementById('navStatus').className = 'nav-status active';
  document.getElementById('navStatusText').textContent = 'Aktif';

  document.getElementById('totalBlinks').textContent = '0';
  document.getElementById('totalAlerts').textContent = '0';
  updateAlerts([]);
  
  // Show calibration overlay if not already calibrated
  if (!isCalibrated) {
    document.getElementById('calibrationOverlay').style.display = 'flex';
  } else {
    document.getElementById('calibrationOverlay').style.display = 'none';
  }
  
  document.getElementById('calibrateBtn').onclick = () => {
    const btn = document.getElementById('calibrateBtn');
    btn.textContent = "Mengkalibrasi...";
    btn.style.opacity = "0.7";
    btn.style.cursor = "wait";
    
    // Tunggu sampai WebSocket siap jika belum terbuka
    const tryCalibrate = () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("calibrate");
      } else {
        setTimeout(tryCalibrate, 500); // coba lagi dalam 500ms
      }
    };
    tryCalibrate();
  };

  sessionInterval = setInterval(tickSession, 1000);
  timerInterval   = setInterval(tickTimer, 1000);
  startCameraAndWebsocket();
}

function stopSession() {
  isActive = false;
  // isCalibrated tidak direset di sini, agar jika mulai sesi lagi tidak perlu kalibrasi ulang
  clearInterval(sessionInterval);
  clearInterval(timerInterval);
  clearInterval(dataInterval); stopCamera();

  document.getElementById('startBtn').innerHTML = `
    <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
    Mulai Sesi`;
  document.getElementById('startBtn').classList.remove('active');
  document.getElementById('navDot').className = 'status-dot';
  document.getElementById('navStatus').className = 'nav-status idle';
  document.getElementById('navStatusText').textContent = 'Siap';
}

function resetSession() {
  stopSession();
  document.getElementById('camIdle').style.display = 'block';
  document.getElementById('camActive').style.display = 'none';
  document.getElementById('camBadge').textContent = 'Standby';
  document.getElementById('camBadge').className = 'cam-badge standby';
  document.getElementById('camRes').textContent = '— × —';

  sessionSeconds  = 0;
  timerSeconds    = 20 * 60;
  totalBlinks     = 0;
  totalAlertCount = 0;
  dataIdx         = 0;
  isCalibrated    = false;
  savedFocalLength = 0;
  
  isCurrentlyFatigued = false;
  isCurrentlyClose = false;
  isCurrentlyLowBlink = false;
  fatigueSeconds = 0;
  closeSeconds = 0;
  lowBlinkSeconds = 0;
  hasHardStopped = false;

  document.getElementById('sessionClock').textContent = '00:00:00';
  document.getElementById('timerNum').textContent = '20:00';
  document.getElementById('timerPct').textContent = '0%';
  document.getElementById('timerBar').style.width = '0%';
  document.getElementById('timerRing').setAttribute('stroke-dashoffset', 0);
  document.getElementById('totalBlinks').textContent = '—';
  document.getElementById('totalAlerts').textContent = '—';
  document.getElementById('durStatus').textContent = '00:00:00';
  document.getElementById('durBar').style.width = '0%';

  document.getElementById('calibrateBtn').textContent = 'Kalibrasi Sekarang';
  document.getElementById('calibrateBtn').style.opacity = '1';
  document.getElementById('calibrateBtn').style.cursor = 'pointer';

  ['statEar','statDist','statBlink','statStatus'].forEach(id => {
    document.getElementById(id).textContent = '—';
    document.getElementById(id).className = 'cam-stat-val';
  });
  document.getElementById('statStatusSub').textContent = '—';
  updateAlerts([]);
}

// ─── TICKS ────────────────────────────────────
function tickSession() {
  if (!isCalibrated) return;
  sessionSeconds++;
  const h = Math.floor(sessionSeconds / 3600);
  const m = Math.floor((sessionSeconds % 3600) / 60);
  const s = sessionSeconds % 60;
  const str = `${pad(h)}:${pad(m)}:${pad(s)}`;
  document.getElementById('sessionClock').textContent = str;
  document.getElementById('durStatus').textContent = str;

  const maxSec = 3 * 3600;
  const pct = Math.min(100, (sessionSeconds / maxSec) * 100);
  document.getElementById('durBar').style.width = pct + '%';

  // Logika 3 Jam + Kelelahan (Hard Stop)
  if (isCurrentlyFatigued) {
    fatigueSeconds++;
  } else {
    fatigueSeconds = 0;
  }

  // Jika durasi melebihi 3 jam dan mata terpantau lelah selama 10 detik berturut-turut
  if (sessionSeconds >= maxSec && fatigueSeconds >= 10 && !hasHardStopped) {
    triggerHardStop();
  }

  // Logika Jarak Terlalu Dekat (10 detik berturut-turut)
  if (isCurrentlyClose) {
    closeSeconds++;
  } else {
    closeSeconds = 0;
  }

  if (closeSeconds >= 10) {
    if (window.Notification && Notification.permission === "granted") {
      new Notification("Waspada Jarak Layar!", {
        body: "Wajah Anda berada terlalu dekat dengan layar. Mundurkan posisi kursi atau tubuh Anda demi kesehatan mata!",
        icon: "icon-192x192.png" 
      });
    }
    // Reset agar tidak spam setiap detik, sehingga perlu 10 detik kedekatan konstan lagi untuk memicu notifikasi baru
    closeSeconds = 0; 
  }

  // Logika Frekuensi Kedip Rendah (10 detik berturut-turut)
  if (isCurrentlyLowBlink) {
    lowBlinkSeconds++;
  } else {
    lowBlinkSeconds = 0;
  }

  if (lowBlinkSeconds >= 10) {
    if (window.Notification && Notification.permission === "granted") {
      new Notification("Waspada Frekuensi Kedip Rendah!", {
        body: "Frekuensi kedipan Anda berada di bawah standar normal (9-17/min). Segera usahakan berkedip dan istirahatkan mata sejenak!",
        icon: "icon-192x192.png" 
      });
    }
    lowBlinkSeconds = 0;
  }
}

function tickTimer() {
  if (!isCalibrated) return;
  if (timerSeconds <= 0) {
    timerSeconds = 20 * 60;
    if (!isResting) triggerRest();
    return;
  }
  timerSeconds--;
  const m = Math.floor(timerSeconds / 60);
  const s = timerSeconds % 60;
  document.getElementById('timerNum').textContent = `${pad(m)}:${pad(s)}`;

  const totalSec = 20 * 60;
  const elapsed  = totalSec - timerSeconds;
  const pct      = Math.round((elapsed / totalSec) * 100);
  document.getElementById('timerPct').textContent = pct + '%';
  document.getElementById('timerBar').style.width = pct + '%';

  const circumference = 188;
  const offset = circumference - (circumference * (timerSeconds / totalSec));
  document.getElementById('timerRing').setAttribute('stroke-dashoffset', offset);

  if (timerSeconds < 60) {
    document.getElementById('timerRing').style.stroke = 'var(--amber)';
  }
}

function updateAlerts(alerts) {
  const list  = document.getElementById('alertsList');
  const count = document.getElementById('alertCount');

  if (alerts.length === 0) {
    list.innerHTML = '<div class="alert-item muted"><div class="alert-text">Belum ada notifikasi. Mulai sesi untuk memantau kondisi mata Anda.</div></div>';
    count.textContent = '0 peringatan';
    return;
  }

  const dangerCount = alerts.filter(a => a.type === 'danger' || a.type === 'warning').length;
  totalAlertCount = dangerCount;
  document.getElementById('totalAlerts').textContent = dangerCount;
  count.textContent = dangerCount + ' peringatan';

  list.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.type}">
      <div class="alert-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round">
          ${a.type === 'danger'
            ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
            : a.type === 'warning'
            ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
            : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
        </svg>
      </div>
      <div class="alert-text">${a.msg}</div>
    </div>
  `).join('');
}

// ─── HARD STOP OVERLAY ────────────────────────
function triggerHardStop() {
  hasHardStopped = true;
  stopSession(); // Hentikan semuanya

  if (window.Notification && Notification.permission === "granted") {
    new Notification("Sesi Selesai (Batas Kelelahan)!", {
      body: "Anda telah menatap layar sangat lama dan mata terlihat lelah. Sistem menghentikan pemantauan. Tolong beristirahatlah dengan cukup!",
      icon: "icon-192x192.png"
    });
  }

  document.getElementById('hardStopOverlay').classList.add('show');
}

function closeHardStop() {
  document.getElementById('hardStopOverlay').classList.remove('show');
  resetSession(); // Memulai bersih kembali semua stat jika user ingin benar-benar lanjut nanti
}

// ─── REST OVERLAY ─────────────────────────────
function triggerRest() {
  if (!isResting) {
    if (isActive) {
      stopSession(); // Jeda sesi otomatis
    }
    
    // Tampilkan notifikasi OS
    if (Notification.permission === "granted") {
      new Notification("Waktunya Istirahat 20-20-20!", {
        body: "Sudah 20 menit! Alihkan pandangan Anda ke objek berjarak ±6 meter selama 20 detik.",
        icon: "icon-192x192.png" // opsional
      });
    }
  }

  isResting   = true;
  restSeconds = 20;
  
  const btnRest = document.getElementById('btnRestSkip');
  btnRest.disabled = true;
  btnRest.style.opacity = '0.5';
  btnRest.style.cursor = 'not-allowed';
  btnRest.textContent = 'Tunggu...';
  
  document.getElementById('restOverlay').classList.add('show');
  document.getElementById('restCount').textContent = restSeconds;
  document.getElementById('restProgress').style.width = '100%';

  restInterval = setInterval(() => {
    restSeconds--;
    if (restSeconds >= 0) {
      document.getElementById('restCount').textContent = restSeconds;
      document.getElementById('restProgress').style.width = ((restSeconds / 20) * 100) + '%';
    }
    if (restSeconds <= 0) {
      clearInterval(restInterval);
      document.getElementById('restCount').textContent = "0";
      btnRest.disabled = false;
      btnRest.style.opacity = '1';
      btnRest.style.cursor = 'pointer';
      btnRest.textContent = 'Lanjutkan Sesi \u2192';
    }
  }, 1000);
}

function finishRest() {
  isResting = false;
  document.getElementById('restOverlay').classList.remove('show');
  timerSeconds = 20 * 60;
  document.getElementById('timerRing').style.stroke = 'var(--green)';
  startSession(); // Otomatis lanjut sesi
}

// ─── UTILS ────────────────────────────────────
function pad(n) { return String(n).padStart(2, '0'); }

// ─── INIT ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
});


/* === FUNGSI DETEKSI WEBSOCKET REALTIME === */
let ws;
let videoStream = null;
let captureInterval;

function startCameraAndWebsocket() {
    const videoElement = document.getElementById('webcamView');
    const hiddenCanvas = document.getElementById('hiddenCanvas');
    const ctx = hiddenCanvas.getContext('2d');
    
    document.getElementById('hudFps').textContent = "Connecting...";

    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    .then((stream) => {
        videoStream = stream;
        videoElement.srcObject = stream;
        
        ws = new WebSocket("ws://localhost:8000/ws/detect");
        
        ws.onopen = () => {
            console.log("Terhubung ke AI Pendeteksi Kelelahan.");
            hiddenCanvas.width = 640;
            hiddenCanvas.height = 480;
            
            // Jika sudah terkalibrasi di frontend, beritahu backend untuk setup state kalibrasi
            if (isCalibrated) {
                ws.send("restore_calibration:" + savedFocalLength);
            }
            
            // Potong frame kamera ke canvas dan kirim (~15 FPS agar pergerakan debugging backend mulus)
            captureInterval = setInterval(() => {
                if(videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                    ctx.drawImage(videoElement, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
                    // kompresi 0.4 sudah lebih dari cukup dan efisien memori base64
                    const base64Data = hiddenCanvas.toDataURL('image/jpeg', 0.4); 
                    ws.send(base64Data);
                }
            }, 66); // Interval 66ms adalah sekitar ~15 FPS
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.calibrating) {
                return; // Wait for the real frame data
            }

            if (data.is_calibrated) {
                isCalibrated = true;
                if (data.focal_length !== undefined) {
                    savedFocalLength = data.focal_length;
                }
                document.getElementById('calibrationOverlay').style.display = 'none';
            } else if (document.getElementById('calibrationOverlay').style.display !== 'flex') {
                 // Kalau backend belum terkalibrasi (misal restart server), tampilkan kembali
                 isCalibrated = false;
                 document.getElementById('calibrationOverlay').style.display = 'flex';
                 return; // Jangan update UI sebelum kalibrasi selesai
            }

            if (!isCalibrated) return;

            // TRACKING STATE FOR 3 HOURS & DISTANCE
            isCurrentlyFatigued = data.current_ear < data.dynamic_threshold;
            isCurrentlyClose = data.distance > 0 && data.distance < 46;
            isCurrentlyLowBlink = data.blink_rate_per_minute > 0 && data.blink_rate_per_minute < 9;

            // HUD Dashboard
            document.getElementById('totalBlinks').textContent = data.total_blinks;
            
            const threshold = data.dynamic_threshold;
            const thresWarn = threshold + 0.02; // sedikit batas peringatan

            const earEl = document.getElementById('statEar');
            earEl.textContent = data.current_ear.toFixed(2);
            earEl.className = 'cam-stat-val ' + (data.current_ear < threshold ? 'danger' : data.current_ear < thresWarn ? 'warning' : 'normal');                                                            
            document.getElementById('statEarSub').textContent = `ambang batas: ${threshold.toFixed(2)}`;
            
            const blinkEl = document.getElementById('statBlink');
            blinkEl.textContent = data.blink_rate_per_minute + '/min';
            blinkEl.className = 'cam-stat-val ' + (data.blink_rate_per_minute < 9 ? 'warning' : 'normal');   

            let statusClass = 'normal';    
              let statusText = data.message.includes("Normal") ? "Normal" : (data.is_drowsy ? "Mengantuk" : "Lelah");
              
              if (data.is_fatigued || data.is_drowsy) { 
                  statusClass = 'danger'; 
              }
              
              if (data.distance > 0 && data.distance < 46) {
                  statusClass = 'danger';
                  if (statusText === "Normal") {
                      statusText = "Jarak Bahaya";
                  }
              } else if (data.distance > 61) {
                  if (statusClass === 'normal') statusClass = 'warning';
              }

              const statusEl = document.getElementById('statStatus');
              statusEl.textContent = statusText;
            statusEl.className = 'cam-stat-val ' + statusClass;
            document.getElementById('statStatusSub').textContent = data.message;
            
            // Progress Bar Status di Sidebar Kanan
            // Skalakan sehingga ambang batas kira-kira di representasikan ke percentage visual
            const earPct = Math.min(100, Math.max(0, (data.current_ear / 0.40) * 100));
            document.getElementById('earBar').style.width = earPct + '%';
            // Hindari lonjakan visual merah yang membuat panik hanya karena pengguna berkedip (1-2 frame)
            document.getElementById('earBar').style.background = data.is_drowsy ? 'var(--red)' : (data.current_ear < threshold ? 'var(--amber)' : 'var(--green)');                                
            document.getElementById('earStatus').textContent = data.is_drowsy ? 'Terpejam Lama' : (data.current_ear < threshold ? 'Berkedip' : 'Melek');                                             
            document.getElementById('earStatus').className = 'metric-status ' + (data.is_drowsy ? 'danger' : data.current_ear < threshold ? 'warning' : 'normal');                        
            
            const distPct = Math.min(100, Math.max(0, (data.distance / 80) * 100));
            if (document.getElementById('distBar')) {
                document.getElementById('distBar').style.width = distPct + '%';
                document.getElementById('distBar').style.background = data.distance < 46 ? 'var(--red)' : data.distance > 61 ? 'var(--amber)' : 'var(--green)';
                document.getElementById('distStatus').textContent = data.distance < 46 ? 'Terlalu Dekat' : data.distance > 61 ? 'Terlalu Jauh' : 'Ideal';
                document.getElementById('distStatus').className = 'metric-status ' + (data.distance < 46 ? 'danger' : data.distance > 61 ? 'warning' : 'normal');
            }
            
            const distEl = document.getElementById('statDist');
            if (distEl) {
                distEl.textContent = data.distance + ' cm';
                distEl.className = 'cam-stat-val ' + (data.distance < 46 ? 'danger' : data.distance > 61 ? 'warning' : 'normal');
            }

            const blinkPct = Math.min(100, (data.blink_rate_per_minute / 17) * 100);
            document.getElementById('blinkBar').style.width  = blinkPct + '%';
            document.getElementById('blinkStatus').textContent = data.blink_rate_per_minute < 9 ? 'Rendah' : data.blink_rate_per_minute > 17 ? 'Tinggi' : 'Normal';                                                
            document.getElementById('blinkStatus').className   = 'metric-status ' + (data.blink_rate_per_minute < 9 ? 'warning' : 'normal'); 

            // Bangun Array Alert untuk Realtime list
            const alerts = [];
            
            // Prioritaskan alert berdasarkan boolean logika backend yang memperhitungkan waktu tahanan (is_fatigued/is_drowsy)
            if (data.distance > 0 && data.distance < 46) alerts.push({ type: 'danger', msg: `Jarak layar terlalu dekat (${data.distance} cm). Standar OSHA: 46–61 cm. Mundurkan kursi atau layar.` });
            
            if (data.is_drowsy) {
                alerts.push({ type: 'danger', msg: `PERINGATAN! MATA TERPEJAM LAMA (MENGANTUK/MICROSLEEP). Istirahat sekarang!` });
            } else if (data.is_fatigued) {
                alerts.push({ type: 'warning', msg: `Kedipan mata berada di laju abnormal. Indikasi Computer Vision Syndrome (CVS).` });
            }

            if (data.blink_rate_per_minute < 9 && data.blink_rate_per_minute > 0) alerts.push({ type: 'warning', msg: `Frekuensi kedip ${data.blink_rate_per_minute}/min di bawah normal. Usahakan berkedip.` });         
            if (sessionSeconds > 3600) alerts.push({ type: 'warning', msg: `Sesi berjalan >1 jam. Pertimbangkan istirahat.` });                     
            
            // Jika tidak ada alert yang critical, pastikan defaultnya rileks
            if (alerts.length === 0) alerts.push({ type: 'info', msg: 'Semua parameter terpantau baik. Pertahankan!' });                  
            updateAlerts(alerts);
        };

        ws.onerror = (err) => {
            console.log('WebSocket Error:', err);
        };
    }).catch((err) => {
        alert("Gagal mengakses kamera! Periksa kembali izin kamera browser Anda.");
    });
}

function stopCamera() {
    if(captureInterval) clearInterval(captureInterval);
    if(ws) ws.close();
    if(videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
}

// ═══════════════════════════════════════════
// PWA & SERVICE WORKER REGISTRATION
// ═══════════════════════════════════════════
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').then((registration) => {
      console.log('ServiceWorker siap mengizinkan aplikasi PWA ini diinstal ke Sistem Operasi.');
    }).catch(err => {
      console.log('ServiceWorker registration gagal: ', err);
    });
  });
}
