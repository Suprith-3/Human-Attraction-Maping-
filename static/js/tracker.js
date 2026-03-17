let sessionId = null;

// Batch counters (reset after every sync)
let pendingKeys = 0;
let pendingClicks = 0;
let pendingActions = 0;
let pendingTabs = 0;
let pendingPixels = 0;

// Session-long totals (never reset until session end, used for UI)
let totalKeystrokes = 0;
let totalClickCount = 0;
let totalActionCount = 0;
let totalTabShiftCount = 0;
let sessionPixels = 0;
let lastTabState = !document.hidden;

// Path tracker
let lastX = null, lastY = null;
let totalPixels = 0;

// Gravity Map Tracker
const GRID_COLS = 20, GRID_ROWS = 20;
let pendingGravityGrid = Array(GRID_ROWS).fill(null).map(() => Array(GRID_COLS).fill(0));
let sessionGravityGrid = Array(GRID_ROWS).fill(null).map(() => Array(GRID_COLS).fill(0));
let mousePoints = [];

// Engagement Tracker
let engagementActive = false;
let engagementTarget = '';
let engagementEndTime = null;
let engagementBreakCount = 0;
let engagementTimerInterval = null;

// Adaptive Blocking
let adaptiveBlockingEnabled = false;
let windowShifts = 0;
let windowStart = Date.now();
const MAX_SHIFTS = 3;
const WINDOW_MS = 2 * 60 * 1000; // 2 minutes
const LOCK_DURATION = 30; // seconds

// Focus Lock
let focusLockActive = false;
let focusLockTarget = '';

// CV Tracker
let cvEnabled = false;

// Offline Tracking
function postTracking(endpoint, payload) {
    if (navigator.onLine) {
        fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).catch(() => queueOffline(endpoint, payload));
    } else {
        queueOffline(endpoint, payload);
    }
}

function queueOffline(endpoint, payload) {
    let queue = JSON.parse(localStorage.getItem('focusos_offline_queue') || '[]');
    queue.push({endpoint, payload});
    localStorage.setItem('focusos_offline_queue', JSON.stringify(queue));
}

window.addEventListener('online', () => {
    let queue = JSON.parse(localStorage.getItem('focusos_offline_queue') || '[]');
    if(queue.length > 0) {
        queue.forEach(item => {
            fetch(item.endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(item.payload)
            }).catch(e => console.error(e));
        });
        localStorage.setItem('focusos_offline_queue', '[]');
    }
});

// Start session manually
async function handleStartSession() {
    try {
        const res = await fetch('/api/session/start', {method: 'POST'});
        const data = await res.json();
        sessionId = data.session_id;
        
        // Reset metrics
        pendingKeys = 0;
        pendingClicks = 0;
        pendingActions = 0;
        pendingTabs = 0;
        pendingPixels = 0;
        
        totalKeystrokes = 0;
        totalClickCount = 0;
        totalActionCount = 0;
        totalTabShiftCount = 0;
        sessionPixels = 0;

        pendingGravityGrid = Array(GRID_ROWS).fill(null).map(() => Array(GRID_COLS).fill(0));
        sessionGravityGrid = Array(GRID_ROWS).fill(null).map(() => Array(GRID_COLS).fill(0));
        mousePoints = [];
        
        // Clear visualization immediately
        const gravityCanvas = document.getElementById('gravityCanvas');
        if (gravityCanvas) {
            const ctx = gravityCanvas.getContext('2d');
            ctx.clearRect(0, 0, gravityCanvas.width, gravityCanvas.height);
        }
        
        const heatmapCanvas = document.getElementById('heatmapCanvas');
        if (heatmapCanvas) {
            const ctx = heatmapCanvas.getContext('2d');
            ctx.clearRect(0, 0, heatmapCanvas.width, heatmapCanvas.height);
        }
        
        // Update UI buttons
        document.getElementById('btn-start-session').style.display = 'none';
        document.getElementById('btn-end-session').style.display = 'inline-block';
        updateLiveBar();
        
        showPopup("🚀 Focus Session Started!");
    } catch (e) {
        console.error("Failed to start session:", e);
    }
}

// End session manually
async function handleEndSession() {
    if (!sessionId) return;
    
    try {
        // Send final batch of data before closing
        await fetch('/api/track/keys', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ count: pendingKeys, session_id: sessionId })
        });
        await fetch('/api/track/mouse', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clicks: pendingClicks, actions: pendingActions, session_id: sessionId })
        });
        await fetch('/api/track/tabs', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ shift_count: pendingTabs, session_id: sessionId })
        });

        const res = await fetch('/api/session/end', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: sessionId,
                tab_shifts: totalTabShiftCount,
                idle_minutes: 0 // Could be enhanced with real idle detection
            })
        });
        
        sessionId = null;
        
        // Update UI buttons
        document.getElementById('btn-start-session').style.display = 'inline-block';
        document.getElementById('btn-end-session').style.display = 'none';
        
        showPopup("✅ Session Saved Successfully!");
        
        // Claim rewards for the session
        await fetch('/api/rewards/claim', { method: 'POST' });
        if (typeof initRewards === 'function') initRewards();

        if (typeof loadHistory === 'function') loadHistory();
    } catch (e) {
        console.error("Failed to end session:", e);
    }
}

// Trackers
document.addEventListener('keydown', (e) => {
    if (!sessionId) return;
    pendingKeys++;
    pendingActions++;
    totalKeystrokes++;
    totalActionCount++;
    updateLiveBar();
});

document.addEventListener('mousedown', () => {
    if (!sessionId) return;
    pendingClicks++;
    pendingActions++;
    totalClickCount++;
    totalActionCount++;
    updateLiveBar();
});

document.addEventListener('scroll', () => {
    if (!sessionId) return;
    pendingActions++;
    totalActionCount++;
});

document.addEventListener('visibilitychange', () => {
    if (!sessionId) return;
    if (document.hidden) {
        pendingTabs++;
        totalTabShiftCount++;
        updateLiveBar();
        handleTabShift(); // triggers engagement alert if active
        checkAdaptiveBlocking();
        if(focusLockActive) handleFocusLock();
    }
});

document.addEventListener('mousemove', (e) => {
    if (!sessionId) return;
    if (lastX !== null) {
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        const dist = Math.sqrt(dx*dx + dy*dy);
        pendingPixels += dist;
        sessionPixels += dist;
    }
    lastX = e.clientX;
    lastY = e.clientY;
    recordGravityPoint(e.clientX, e.clientY);
    updateLiveBar(); // update cm live
});

function getDistanceCm() {
    return (sessionPixels * 0.026458).toFixed(1);
}

function updateLiveBar() {
    const elmKeys = document.getElementById('stat-keys');
    if (elmKeys) elmKeys.textContent = totalKeystrokes;
    const elmClicks = document.getElementById('stat-clicks');
    if (elmClicks) elmClicks.textContent = totalClickCount;
    const elmActions = document.getElementById('stat-actions');
    if (elmActions) elmActions.textContent = totalActionCount;
    const elmTabs = document.getElementById('stat-tabs');
    if (elmTabs) elmTabs.textContent = totalTabShiftCount;
    const elmPath = document.getElementById('stat-path-cm');
    if (elmPath) elmPath.textContent = getDistanceCm();
}

function recordGravityPoint(x, y) {
    const col = Math.floor((x / window.innerWidth) * GRID_COLS);
    const row = Math.floor((y / window.innerHeight) * GRID_ROWS);
    if (row >= 0 && row < GRID_ROWS && col >= 0 && col < GRID_COLS) {
        pendingGravityGrid[row][col]++;
        sessionGravityGrid[row][col]++;
    }
    // Also save points for heatmap
    if(Math.random() < 0.1) { // sample 10% points to prevent massive arrays
        mousePoints.push({x, y});
    }
}

// Render Gravity Map with enhanced visuals
function renderGravityMap() {
    const canvas = document.getElementById('gravityCanvas');
    if(canvas) {
        const ctx = canvas.getContext('2d');
        const cellW = canvas.width / GRID_COLS;
        const cellH = canvas.height / GRID_ROWS;
        
        ctx.fillStyle = '#050510';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw subtle grid lines
        ctx.strokeStyle = '#1a1a2e';
        ctx.lineWidth = 1;
        for(let i=0; i<=GRID_COLS; i++) {
            ctx.beginPath(); ctx.moveTo(i*cellW, 0); ctx.lineTo(i*cellW, canvas.height); ctx.stroke();
        }
        for(let i=0; i<=GRID_ROWS; i++) {
            ctx.beginPath(); ctx.moveTo(0, i*cellH); ctx.lineTo(canvas.width, i*cellH); ctx.stroke();
        }

        if (!sessionId) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '20px "Courier New"';
            ctx.textAlign = 'center';
            ctx.fillText("WAITING FOR SESSION START...", canvas.width/2, canvas.height/2);
        } else {
            const maxVal = Math.max(...sessionGravityGrid.flat()) || 1;
            for (let r = 0; r < GRID_ROWS; r++) {
                for (let c = 0; c < GRID_COLS; c++) {
                    const val = sessionGravityGrid[r][c];
                    if (val > 0) {
                        const intensity = val / maxVal;
                        // Color: Indigo-Blue (low) → Neon Cyan → Hot Pink (high)
                        const hue = 260 - (intensity * 300); // 260 (purple) to -40 (red/pink)
                        ctx.fillStyle = `hsla(${hue}, 100%, 60%, ${0.3 + intensity * 0.7})`;
                        ctx.shadowBlur = 10 * intensity;
                        ctx.shadowColor = `hsla(${hue}, 100%, 50%, 0.8)`;
                        ctx.fillRect(c * cellW + 1, r * cellH + 1, cellW - 2, cellH - 2);
                        ctx.shadowBlur = 0;
                    }
                }
            }
        }
    }
    requestAnimationFrame(renderGravityMap);
}
renderGravityMap();

// Batch sending
setInterval(() => {
    if(!sessionId) return;
    postTracking('/api/track/keys', { count: pendingKeys, session_id: sessionId });
    postTracking('/api/track/mouse', { clicks: pendingClicks, actions: pendingActions, session_id: sessionId });
    postTracking('/api/track/tabs', { shift_count: pendingTabs, session_id: sessionId });
    postTracking('/api/track/path', { total_pixels: pendingPixels, total_cm: parseFloat((pendingPixels * 0.026458).toFixed(1)), session_id: sessionId });
    postTracking('/api/track/gravity', { grid_json: JSON.stringify(pendingGravityGrid), session_id: sessionId });
    if (mousePoints.length > 0) {
        postTracking('/api/track/heatmap', { points: mousePoints, session_id: sessionId });
        mousePoints = [];
    }
    
    // Reset batch counters after sending (UI continues using session totals)
    pendingKeys = 0;
    pendingClicks = 0;
    pendingActions = 0;
    pendingTabs = 0;
    pendingPixels = 0;
    lastX = null;
    lastY = null;
    pendingGravityGrid = Array(GRID_ROWS).fill(null).map(() => Array(GRID_COLS).fill(0));
}, 30000);

// --- Engagement ---
function initEngagement() {
    const target = document.getElementById('engage-target').value;
    const duration = parseInt(document.getElementById('engage-duration').value);
    if (!target || !duration) return alert("Please fill both fields.");
    
    startEngagement(target, duration);
    
    document.getElementById('engage-status').style.display = 'block';
    document.getElementById('engage-active-target').textContent = target;
}

function startEngagement(target, durationMinutes) {
    engagementActive = true;
    engagementTarget = target;
    engagementEndTime = Date.now() + durationMinutes * 60 * 1000;
    engagementBreakCount = 0;
    
    if (engagementTimerInterval) clearInterval(engagementTimerInterval);
    engagementTimerInterval = setInterval(() => {
        const remaining = engagementEndTime - Date.now();
        if (remaining <= 0) {
            clearInterval(engagementTimerInterval);
            engagementActive = false;
            document.getElementById('engage-timer').textContent = "00:00";
            postTracking('/api/track/engagement', {
                target_app: engagementTarget,
                planned_duration: durationMinutes,
                actual_focus_time: durationMinutes, // Simplified calculation for now
                break_count: engagementBreakCount
            });
            alert("Engagement Session Completed!");
        } else {
            const m = Math.floor(remaining / 60000);
            const s = Math.floor((remaining % 60000) / 1000);
            document.getElementById('engage-timer').textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function handleTabShift() {
    if (!engagementActive) return;
    engagementBreakCount++;
    playDogBark();
    flashScreen();
    showPopup(`⚠️ Focus Break! Return to ${engagementTarget}`);
}

function playDogBark() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        
        const playBark = (startTime) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(150, startTime);
            osc.frequency.exponentialRampToValueAtTime(40, startTime + 0.15);
            
            gain.gain.setValueAtTime(0.5, startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.2);
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc.start(startTime);
            osc.stop(startTime + 0.2);
        };

        // Play a series of barks over 5 seconds
        for (let i = 0; i < 5; i++) {
            playBark(audioCtx.currentTime + i);
            playBark(audioCtx.currentTime + i + 0.2); // Double bark "Ruff-ruff"
        }
        
        setTimeout(() => audioCtx.close(), 6000);
    } catch(e) {
        console.error("Audio error:", e);
    }
}

function flashScreen() {
    const overlay = document.getElementById('flash-overlay');
    if (!overlay) return;
    let count = 0;
    const colors = ['rgba(255,0,0,0.3)', 'rgba(0,255,0,0.3)'];
    const interval = setInterval(() => {
        overlay.style.background = colors[count % 2];
        overlay.style.display = 'block';
        count++;
        if (count >= 6) { clearInterval(interval); overlay.style.display = 'none'; }
    }, 500);
}

function showPopup(msg) {
    const div = document.createElement('div');
    div.style.position = 'fixed';
    div.style.top = '20px';
    div.style.left = '50%';
    div.style.transform = 'translateX(-50%)';
    div.style.background = '#ff4444';
    div.style.color = '#fff';
    div.style.padding = '15px 30px';
    div.style.borderRadius = '8px';
    div.style.zIndex = '999999';
    div.style.fontWeight = 'bold';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

// --- Adaptive Blocking ---
function toggleAdaptive(checked) {
    adaptiveBlockingEnabled = checked;
    if(checked) {
        windowShifts = 0; 
        windowStart = Date.now();
        updateAdaptiveDisplay();
    }
}

function updateAdaptiveDisplay() {
    const display = document.getElementById('adaptive-shifts-text');
    if(display) display.textContent = `Shifts: ${windowShifts}/${MAX_SHIFTS}`;
}

function checkAdaptiveBlocking() {
    if (!adaptiveBlockingEnabled) return;
    const now = Date.now();
    if (now - windowStart > WINDOW_MS) {
        windowShifts = 0;
        windowStart = now;
    }
    windowShifts++;
    updateAdaptiveDisplay();

    if (windowShifts >= MAX_SHIFTS) {
        triggerAdaptiveLock();
    }
}

function triggerAdaptiveLock() {
    const overlay = document.getElementById('adaptive-lock-overlay');
    overlay.style.display = 'flex';
    
    // Block all input events (Mouse, Keyboard, Scroll, Selection, etc.)
    const blockInput = (e) => {
        if (overlay.style.display === 'flex') {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    };
    
    // Attempt to lock pointer (traps mouse inside the window)
    const requestLock = (e) => {
        if (e && e.type === 'click') blockInput(e);
        try {
            if (overlay.requestPointerLock) {
                overlay.requestPointerLock();
            }
        } catch(err) {}
    };
    
    // Try immediate (might fail without gesture)
    requestLock();
    // Also lock on first click to the overlay (ensures it eventually locks)
    overlay.onclick = requestLock;

    // Register all blocking listeners
    const blockEvents = [
        'keydown', 'keyup', 'keypress', 
        'mousedown', 'mouseup', 'click', 'dblclick', 'mousemove', 'contextmenu',
        'wheel', 'mousewheel', 'DOMMouseScroll',
        'touchstart', 'touchend', 'touchmove',
        'selectstart', 'copy', 'paste', 'cut'
    ];
    
    blockEvents.forEach(evtName => {
        document.addEventListener(evtName, blockInput, true);
    });

    // Force re-lock if user tries to escape pointer lock
    const handleLockChange = () => {
        if (document.pointerLockElement !== overlay && overlay.style.display === 'flex') {
            requestLock();
        }
    };
    document.addEventListener('pointerlockchange', handleLockChange);

    let secs = LOCK_DURATION;
    const countdown = document.getElementById('adaptive-countdown');
    countdown.textContent = secs;
    const timer = setInterval(() => {
        secs--;
        countdown.textContent = secs;
        if (secs <= 0) {
            clearInterval(timer);
            overlay.style.display = 'none';
            
            // Release lock and all listeners
            document.exitPointerLock();
            blockEvents.forEach(evtName => {
                document.removeEventListener(evtName, blockInput, true);
            });
            document.removeEventListener('pointerlockchange', handleLockChange);
            
            windowShifts = 0;
            windowStart = Date.now();
            updateAdaptiveDisplay();
        }
    }, 1000);

    postTracking('/api/blocking/event', { shift_count: windowShifts });
}

// --- Focus Lock ---
function toggleFocusLock() {
    const target = document.getElementById('focus-lock-target').value;
    const btn = document.getElementById('btn-focus-lock');
    if(focusLockActive) {
        focusLockActive = false;
        btn.textContent = 'Activate Lock';
        btn.style.background = 'var(--accent)';
    } else {
        if(!target) return alert('Enter target app/URL first');
        focusLockActive = true;
        focusLockTarget = target;
        btn.textContent = 'Deactivate Lock';
        btn.style.background = 'var(--accent-red)';
    }
}

function handleFocusLock() {
    const overlay = document.getElementById('focus-lock-overlay');
    document.getElementById('lock-target-name').textContent = focusLockTarget;
    overlay.style.display = 'flex';
    
    let secs = 5;
    const cd = document.getElementById('lock-countdown');
    const overrideBtn = document.getElementById('override-btn');
    overrideBtn.style.display = 'none';
    cd.style.display = 'block';
    
    cd.textContent = `Overriding in ${secs}...`;
    let lockTimer = setInterval(() => {
        if(!document.hidden) {
            clearInterval(lockTimer);
            overlay.style.display = 'none';
            return;
        }
        secs--;
        cd.textContent = `Overriding in ${secs}...`;
        if (secs <= 0) {
            clearInterval(lockTimer);
            cd.style.display = 'none';
            overrideBtn.style.display = 'block';
        }
    }, 1000);
}

function overrideFocusLock() {
    const overlay = document.getElementById('focus-lock-overlay');
    overlay.style.display = 'none';
    postTracking('/api/focuslock/event', { target_app: focusLockTarget, overridden: 1 });
}

// --- CV Attention Detection ---
function toggleCV(checked) {
    cvEnabled = checked;
    postTracking('/api/cv/toggle', {enabled: checked});
}

setInterval(async () => {
    if (!cvEnabled || !navigator.onLine) return;
    try {
        const res = await fetch('/api/cv/alerts/poll');
        const data = await res.json();
        data.alerts.forEach(alert => {
            playDogBark();
            flashScreen();
            showPopup(alert.type === 'no_face'
                ? '👁️ You look away! Please refocus.'
                : '😴 Head bend detected! Stay alert.');
        });
    } catch(e) {}
}, 500);
