from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
import bcrypt
import time
from database import get_db, init_db, log_cv_alert

app = Flask(__name__)
app.secret_key = 'super_secret_offline_key'

# Initialize DB
init_db()

# Client-side CV alerts are logged via /api/cv/alert/log

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('dashboard.html', user=user)

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'})
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, hashed))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_stats (user_id, last_session_date) VALUES (?, date('now'))", (user_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Email already exists or error occurred.'})
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        session['user_id'] = user['id']
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/session/start', methods=['POST'])
@login_required
def api_session_start():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (user_id, start_time) VALUES (?, datetime('now', 'localtime'))", (user_id,))
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return jsonify({'session_id': session_id})

@app.route('/api/session/end', methods=['POST'])
@login_required
def api_session_end():
    user_id = session['user_id']
    data = request.json
    session_id = data.get('session_id')
    tab_shifts = data.get('tab_shifts', 0)
    idle_minutes = data.get('idle_minutes', 0)
    
    focus_score = max(0, 100 - (tab_shifts * 5) - idle_minutes)
    
    conn = get_db()
    conn.execute("UPDATE sessions SET end_time = datetime('now', 'localtime'), focus_score = ? WHERE id = ? AND user_id = ?", (focus_score, session_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/track/keys', methods=['POST'])
@login_required
def api_track_keys():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO key_events (user_id, session_id, count) VALUES (?, ?, ?)", (user_id, data.get('session_id'), data.get('count', 0)))
    if data.get('session_id'):
        conn.execute("UPDATE sessions SET keystrokes = keystrokes + ? WHERE id = ?", (data.get('count', 0), data.get('session_id')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/mouse', methods=['POST'])
@login_required
def api_track_mouse():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO mouse_events (user_id, session_id, clicks, actions) VALUES (?, ?, ?, ?)", (user_id, data.get('session_id'), data.get('clicks', 0), data.get('actions', 0)))
    if data.get('session_id'):
        conn.execute("UPDATE sessions SET clicks = clicks + ?, actions = actions + ? WHERE id = ?", (data.get('clicks', 0), data.get('actions', 0), data.get('session_id')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/tabs', methods=['POST'])
@login_required
def api_track_tabs():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO tab_events (user_id, session_id, shift_count) VALUES (?, ?, ?)", (user_id, data.get('session_id'), data.get('shift_count', 0)))
    if data.get('session_id'):
        conn.execute("UPDATE sessions SET tab_shifts = tab_shifts + ? WHERE id = ?", (data.get('shift_count', 0), data.get('session_id')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/path', methods=['POST'])
@login_required
def api_track_path():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO mouse_path (user_id, session_id, total_pixels, total_cm) VALUES (?, ?, ?, ?)", (user_id, data.get('session_id'), data.get('total_pixels', 0), data.get('total_cm', 0)))
    if data.get('session_id'):
        conn.execute("UPDATE sessions SET mouse_px = mouse_px + ?, mouse_cm = mouse_cm + ? WHERE id = ?", (data.get('total_pixels', 0), data.get('total_cm', 0), data.get('session_id')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/heatmap', methods=['POST'])
@login_required
def api_track_heatmap():
    user_id = session['user_id']
    data = request.json
    pts = data.get('points', [])
    sess_id = data.get('session_id')
    conn = get_db()
    for p in pts:
        conn.execute("INSERT INTO heatmap_points (user_id, session_id, x, y) VALUES (?, ?, ?, ?)", (user_id, sess_id, p['x'], p['y']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/gravity', methods=['POST'])
@login_required
def api_track_gravity():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO gravity_maps (user_id, session_id, grid_json, app_label) VALUES (?, ?, ?, ?)", (user_id, data.get('session_id'), data.get('grid_json', '[]'), data.get('app_label', '')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/track/engagement', methods=['POST'])
@login_required
def api_track_engagement():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO engagement_sessions (user_id, target_app, planned_duration, actual_focus_time, break_count) VALUES (?, ?, ?, ?, ?)", 
                 (user_id, data.get('target_app'), data.get('planned_duration'), data.get('actual_focus_time'), data.get('break_count')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/stats/realtime')
@login_required
def api_stats_realtime():
    from datetime import datetime, timedelta
    user_id = session['user_id']
    conn = get_db()
    
    # 1. Get current active session
    curr = conn.execute("SELECT id, start_time FROM sessions WHERE user_id = ? AND end_time IS NULL ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    if not curr:
        conn.close()
        return jsonify({'labels':[], 'keystrokes':[], 'clicks':[], 'actions':[], 'tab_shifts':[], 'mouse_cm':[]})

    session_id = curr['id']
    start_str = curr['start_time'] # e.g. "2026-03-20 11:17:00"
    
    # Standardize start_time for range generation
    try:
        # SQLite datetime format is usually YYYY-MM-DD HH:MM:SS
        start_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
    except:
        start_dt = datetime.now() - timedelta(minutes=5)

    now = datetime.now()
    
    # 2. Generate Second-by-Second Bucket Map
    labels = []
    data_map = {}
    
    # Show last 2 minutes second-by-second for ultra-high resolution
    resol_start = max(start_dt, now - timedelta(minutes=2))
    
    temp_dt = resol_start.replace(microsecond=0)
    while temp_dt <= now:
        lbl = temp_dt.strftime('%H:%M:%S')
        labels.append(lbl)
        data_map[lbl] = {'k':0, 'c':0, 'a':0, 't':0, 'm':0}
        temp_dt += timedelta(seconds=1)

    # 3. Pull Real Data from Database for this session (per second)
    def fill_stat(table, col, map_key):
        rows = conn.execute(f"SELECT strftime('%H:%M:%S', timestamp, 'localtime') as sec, SUM({col}) as total FROM {table} WHERE session_id = ? GROUP BY sec", (session_id,)).fetchall()
        for r in rows:
            if r['sec'] in data_map:
                data_map[r['sec']][map_key] = r['total']

    try:
        fill_stat('key_events', 'count', 'k')
        fill_stat('mouse_events', 'clicks', 'c')
        rows_a = conn.execute("SELECT strftime('%H:%M:%S', timestamp, 'localtime') as sec, SUM(actions) as total FROM mouse_events WHERE session_id = ? GROUP BY sec", (session_id,)).fetchall()
        for r in rows_a:
            if r['sec'] in data_map:
                data_map[r['sec']]['a'] = r['total']
        
        fill_stat('tab_events', 'shift_count', 't')
        fill_stat('mouse_path', 'total_cm', 'm')
    except Exception as e:
        print(f"Error fetching stats: {e}")
    
    conn.close()

    # 4. Final lists
    return jsonify({
        'labels': labels,
        'keystrokes': [data_map[l]['k'] for l in labels],
        'clicks': [data_map[l]['c'] for l in labels],
        'actions': [data_map[l]['a'] for l in labels],
        'tab_shifts': [data_map[l]['t'] for l in labels],
        'mouse_cm': [round(data_map[l]['m'] or 0, 2) for l in labels]
    })

@app.route('/api/stats/history')
@login_required
def api_stats_history():
    user_id = session['user_id']
    conn = get_db()
    rows = conn.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 30", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats/heatmap')
@login_required
def api_stats_heatmap():
    user_id = session['user_id']
    conn = get_db()
    rows = conn.execute("SELECT x, y FROM heatmap_points WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1000", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats/intensity')
@login_required
def api_stats_intensity():
    import random
    data = [random.randint(0, 1000) for _ in range(24)]
    return jsonify({'hours': list(range(24)), 'intensity': data})

@app.route('/api/stats/distribution')
@login_required
def api_stats_distribution():
    user_id = session['user_id']
    conn = get_db()
    # Get sums of all interactions for the user
    stats = conn.execute("""
        SELECT 
            SUM(keystrokes) as keys, 
            SUM(clicks) as clicks, 
            SUM(tab_shifts) as tabs
        FROM sessions 
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    conn.close()

    keys = stats['keys'] or 0
    clicks = stats['clicks'] or 0
    tabs = stats['tabs'] or 0
    
    total = keys + clicks + tabs
    if total == 0:
        return jsonify({'keyboard': 33, 'mouse': 33, 'idle': 0, 'tab': 34})
    
    return jsonify({
        'keyboard': round((keys / total) * 100),
        'mouse': round((clicks / total) * 100),
        'idle': 5, # Placeholder for now as we don't track pure idle time yet
        'tab': round((tabs / total) * 100)
    })

@app.route('/api/stats/flow')
@login_required
def api_stats_flow():
    return jsonify({
        'start_deep': 10,
        'deep_tab': 5,
        'tab_break': 3,
        'break_return': 2,
        'return_end': 8
    })

@app.route('/api/cv/alert/log', methods=['POST'])
@login_required
def api_cv_alert_log():
    user_id = session['user_id']
    data = request.json
    alert_type = data.get('type', 'no_face')
    log_cv_alert(user_id, alert_type)
    return jsonify({'status': 'ok'})

@app.route('/api/blocking/event', methods=['POST'])
@login_required
def api_blocking_event():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO blocking_events (user_id, shift_count, blocked_at) VALUES (?, ?, datetime('now', 'localtime'))", (user_id, data.get('shift_count')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/focuslock/event', methods=['POST'])
@login_required
def api_focuslock_event():
    user_id = session['user_id']
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO focus_lock_events (user_id, target_app, attempted_switch_time, overridden) VALUES (?, ?, datetime('now', 'localtime'), ?)", (user_id, data.get('target_app'), data.get('overridden', 0)))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/rewards', methods=['GET'])
@login_required
def api_rewards():
    user_id = session['user_id']
    conn = get_db()
    stats = conn.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
    badges = conn.execute("SELECT reward_type FROM rewards WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    
    if stats:
        return jsonify({
            'coins': stats['total_coins'],
            'streak': stats['streak_days'],
            'badges': [b['reward_type'] for b in badges]
        })
    return jsonify({'coins': 0, 'streak': 0, 'badges': []})

@app.route('/api/rewards/claim', methods=['POST'])
@login_required
def api_rewards_claim():
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    reward_type = data.get('reward_type', 'session_complete')
    
    # Mastery Shop purchases
    purchase_badges = ['deep_work_master', 'flow_achiever', 'switch_slayer']
    cost = 2000 if reward_type in purchase_badges else 0
    earn = 50 if reward_type == 'session_complete' else 0

    conn = get_db()
    if cost > 0:
        stats = conn.execute("SELECT total_coins FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
        if not stats or stats['total_coins'] < cost:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Insufficient coins'})
        conn.execute("UPDATE user_stats SET total_coins = total_coins - ? WHERE user_id = ?", (cost, user_id))
    
    conn.execute("INSERT INTO rewards (user_id, reward_type) VALUES (?, ?)", (user_id, reward_type))
    
    if earn > 0:
        conn.execute("UPDATE user_stats SET total_coins = total_coins + ? WHERE user_id = ?", (earn, user_id))
        
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
