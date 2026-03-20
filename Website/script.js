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
  
  // Show calibration overlay
  document.getElementById('calibrationOverlay').style.display = 'flex';
  
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

  document.getElementById('sessionClock').textContent = '00:00:00';
  document.getElementById('timerNum').textContent = '20:00';
  document.getElementById('timerPct').textContent = '0%';
  document.getElementById('timerBar').style.width = '0%';
  document.getElementById('timerRing').setAttribute('stroke-dashoffset', 47);
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
}

function tickTimer() {
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

// ─── DATA UPDATE ──────────────────────────────
// function updateData() {
//   if (!isActive) return;
//   const ear   = earData[dataIdx % earData.length];
//   const dist  = distData[dataIdx % distData.length];
//   const blink = blinkData[dataIdx % blinkData.length];
//   dataIdx++;

//   const earV   = +(ear  + (Math.random() - 0.5) * 0.02).toFixed(2);
//   const distV  = Math.round(dist  + (Math.random() - 0.5) * 4);
//   const blinkV = Math.round(blink + (Math.random() - 0.5) * 2);

//   totalBlinks += Math.round(blinkV / 30);
//   document.getElementById('totalBlinks').textContent = totalBlinks;

//   // HUD
//   document.getElementById('hudEar').textContent   = earV.toFixed(2);
//   document.getElementById('hudDist').textContent  = distV + ' cm';
//   document.getElementById('hudBlink').textContent = blinkV + '/min';
//   document.getElementById('hudFps').textContent   = (29 + Math.random()).toFixed(1) + ' fps';
//   document.getElementById('hudConf').textContent  = (97 + Math.random()).toFixed(1) + '%';

//   // Stats bar
//   const earEl = document.getElementById('statEar');
//   earEl.textContent = earV.toFixed(2);
//   earEl.className = 'cam-stat-val ' + (earV < 0.25 ? 'danger' : earV < 0.27 ? 'warning' : 'normal');

//   const distEl = document.getElementById('statDist');
//   distEl.textContent = distV + ' cm';
//   distEl.className = 'cam-stat-val ' + (distV < 46 ? 'danger' : distV > 61 ? 'warning' : 'normal');

//   const blinkEl = document.getElementById('statBlink');
//   blinkEl.textContent = blinkV + '/min';
//   blinkEl.className = 'cam-stat-val ' + (blinkV < 12 ? 'warning' : 'normal');

//   let status = 'Normal', statusClass = 'normal', statusSub = 'Kondisi baik';
//   if      (earV < 0.25 || distV < 38) { status = 'Tinggi'; statusClass = 'danger';  statusSub = 'Kelelahan terdeteksi'; }
//   else if (earV < 0.27 || distV < 46) { status = 'Sedang'; statusClass = 'warning'; statusSub = 'Perlu perhatian'; }

//   const statusEl = document.getElementById('statStatus');
//   statusEl.textContent = status;
//   statusEl.className = 'cam-stat-val ' + statusClass;
//   document.getElementById('statStatusSub').textContent = statusSub;

//   // Metric bars
//   const earPct = Math.min(100, Math.max(0, (1 - earV / 0.35) * 100));
//   document.getElementById('earBar').style.width      = earPct + '%';
//   document.getElementById('earBar').style.background = earV < 0.25 ? 'var(--red)' : earV < 0.27 ? 'var(--amber)' : 'var(--green)';
//   document.getElementById('earStatus').textContent   = earV < 0.25 ? 'Kelelahan' : earV < 0.27 ? 'Sedang' : 'Normal';
//   document.getElementById('earStatus').className     = 'metric-status ' + (earV < 0.25 ? 'danger' : earV < 0.27 ? 'warning' : 'normal');

//   const distPct = Math.min(100, Math.max(0, (distV / 80) * 100));
//   document.getElementById('distBar').style.width      = distPct + '%';
//   document.getElementById('distBar').style.background = distV < 46 ? 'var(--red)' : distV > 61 ? 'var(--amber)' : 'var(--green)';
//   document.getElementById('distStatus').textContent   = distV < 46 ? 'Terlalu Dekat' : distV > 61 ? 'Terlalu Jauh' : 'Ideal';
//   document.getElementById('distStatus').className     = 'metric-status ' + (distV < 46 ? 'danger' : distV > 61 ? 'warning' : 'normal');

//   const blinkPct = Math.min(100, (blinkV / 20) * 100);
//   document.getElementById('blinkBar').style.width  = blinkPct + '%';
//   document.getElementById('blinkStatus').textContent = blinkV < 12 ? 'Rendah' : blinkV > 20 ? 'Tinggi' : 'Normal';
//   document.getElementById('blinkStatus').className   = 'metric-status ' + (blinkV < 12 ? 'warning' : 'normal');

//   // Build alerts
//   const alerts = [];
//   if (distV < 46)  alerts.push({ type: 'danger',  msg: `Jarak layar terlalu dekat (${distV} cm). Standar OSHA: 46–61 cm. Mundurkan kursi atau layar.` });
//   if (earV < 0.25) alerts.push({ type: 'danger',  msg: `EAR Score ${earV.toFixed(2)} menunjukkan kelelahan mata yang signifikan. Istirahat sekarang.` });
//   else if (earV < 0.27) alerts.push({ type: 'warning', msg: `EAR Score ${earV.toFixed(2)} mendekati ambang batas kelelahan (0.25).` });
//   if (blinkV < 12) alerts.push({ type: 'warning', msg: `Frekuensi kedip ${blinkV}/min di bawah normal (12–20/min). Usahakan berkedip lebih sering.` });
//   if (sessionSeconds > 3600) alerts.push({ type: 'warning', msg: `Sesi berjalan lebih dari 1 jam. Pertimbangkan istirahat lebih panjang.` });
//   if (alerts.length === 0) alerts.push({ type: 'info', msg: 'Semua parameter dalam kondisi baik. Pertahankan posisi dan jarak layar Anda.' });

//   updateAlerts(alerts);
// }

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

// ─── REST OVERLAY ─────────────────────────────
function triggerRest() {
  isResting   = true;
  restSeconds = 20;
  document.getElementById('restOverlay').classList.add('show');
  document.getElementById('restCount').textContent = restSeconds;
  document.getElementById('restProgress').style.width = '100%';

  restInterval = setInterval(() => {
    restSeconds--;
    document.getElementById('restCount').textContent = restSeconds;
    document.getElementById('restProgress').style.width = ((restSeconds / 20) * 100) + '%';
    if (restSeconds <= 0) skipRest();
  }, 1000);
}

function skipRest() {
  clearInterval(restInterval);
  isResting = false;
  document.getElementById('restOverlay').classList.remove('show');
  timerSeconds = 20 * 60;
  document.getElementById('timerRing').style.stroke = 'var(--green)';
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
                document.getElementById('calibrationOverlay').style.display = 'none';
            } else if (document.getElementById('calibrationOverlay').style.display !== 'flex') {
                 // Kalau backend belum terkalibrasi (misal restart server), tampilkan kembali
                 document.getElementById('calibrationOverlay').style.display = 'flex';
                 return; // Jangan update UI sebelum kalibrasi selesai
            }
            
            // HUD Dalam Video
            document.getElementById('hudEar').textContent = data.current_ear.toFixed(2);
            document.getElementById('hudDist').textContent = data.distance + ' cm';
            document.getElementById('hudBlink').textContent = data.blink_rate_per_minute + '/min';
            document.getElementById('hudFps').textContent   = "LIVE FPS: ~7.0 fps";
            document.getElementById('hudConf').textContent  = "100.0%"; // As CNN confidence is abstracted
            
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
            blinkEl.className = 'cam-stat-val ' + (data.blink_rate_per_minute < 12 ? 'warning' : 'normal');   

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

            const blinkPct = Math.min(100, (data.blink_rate_per_minute / 20) * 100);
            document.getElementById('blinkBar').style.width  = blinkPct + '%';
            document.getElementById('blinkStatus').textContent = data.blink_rate_per_minute < 12 ? 'Rendah' : data.blink_rate_per_minute > 20 ? 'Tinggi' : 'Normal';                                                
            document.getElementById('blinkStatus').className   = 'metric-status ' + (data.blink_rate_per_minute < 12 ? 'warning' : 'normal'); 

            // Bangun Array Alert untuk Realtime list
            const alerts = [];
            
            // Prioritaskan alert berdasarkan boolean logika backend yang memperhitungkan waktu tahanan (is_fatigued/is_drowsy)
            if (data.distance > 0 && data.distance < 46) alerts.push({ type: 'danger', msg: `Jarak layar terlalu dekat (${data.distance} cm). Standar OSHA: 46–61 cm. Mundurkan kursi atau layar.` });
            
            if (data.is_drowsy) {
                alerts.push({ type: 'danger', msg: `PERINGATAN! MATA TERPEJAM LAMA (MENGANTUK/MICROSLEEP). Istirahat sekarang!` });
            } else if (data.is_fatigued) {
                alerts.push({ type: 'warning', msg: `Kedipan mata berada di laju abnormal. Indikasi Computer Vision Syndrome (CVS).` });
            }

            if (data.blink_rate_per_minute < 12 && data.blink_rate_per_minute > 0) alerts.push({ type: 'warning', msg: `Frekuensi kedip ${data.blink_rate_per_minute}/min di bawah normal. Usahakan berkedip.` });         
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
