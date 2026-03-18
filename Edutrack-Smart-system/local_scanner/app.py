import os, cv2, sqlite3, time, csv
from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
from recognizer import get_present_rolls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "frontend/templates"), 
            static_folder=os.path.join(BASE_DIR, "frontend/static"))
app.secret_key = "SMART_KEY_2026"

# Initialize SocketIO for real-time WebSocket communication
socketio = SocketIO(app, async_mode='eventlet')

# Global Tracking Logic
tracking = {"active": False, "hits": {}, "total_checks": 0, "subject": "", "log": []}

def init_db():
    conn = sqlite3.connect("attendance.db")
    conn.execute('CREATE TABLE IF NOT EXISTS faculty (emp_id TEXT PRIMARY KEY, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, class TEXT)')
    conn.execute('''CREATE TABLE IF NOT EXISTS attendance_logs 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT, subject TEXT, date TEXT, status TEXT)''')
    
    # Real-Time DB Query Optimization (B-Tree Indexes for fast aggregation)
    conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON attendance_logs(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON attendance_logs(date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_subject ON attendance_logs(subject)')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def gatekeeper():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect('/')
    return render_template('dashboard.html', is_active=tracking["active"], tracking_log=tracking.get("log", []))

@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    tracking.update({
        "active": True,
        "hits": {},
        "total_checks": 0,
        "subject": request.form.get('subject', 'General'),
        "log": [f"Session Started: {request.form.get('subject')}", "Scanner: ACTIVE"]
    })
    return redirect(url_for('dashboard'))

@app.route('/stop_attendance')
def stop_attendance():
    # FIX: Guard against DivisionByZero if no frames were processed
    if tracking["active"] and tracking["total_checks"] > 0:
        conn = sqlite3.connect("attendance.db")
        for roll, count in tracking["hits"].items():
            presence = (count / tracking["total_checks"]) * 100
            status = "PRESENT" if presence >= 50 else "ABSENT"
            conn.execute("INSERT INTO attendance_logs (roll, subject, date, status) VALUES (?, ?, ?, ?)", 
                         (roll, tracking["subject"], time.strftime("%Y-%m-%d"), status))
        conn.commit()
        conn.close()
    tracking["active"] = False
    return redirect(url_for('records'))
5
@app.route('/video_feed')
def video_feed():
    def gen():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while True:
            ret, frame = cap.read()
            if not ret: break
            if tracking["active"]:
                tracking["total_checks"] += 1
                try:
                    present_rolls = get_present_rolls(frame)
                    new_detections = False
                    for match in present_rolls:
                        roll, conf = match if isinstance(match, tuple) else (match, 85)
                        if roll not in tracking["hits"]:
                            tracking["hits"][roll] = 0
                            new_detections = True
                            
                            # Fetch Student Name to enrich the websocket payload
                            conn = sqlite3.connect("attendance.db")
                            student = conn.execute("SELECT name FROM students WHERE roll=?", (roll,)).fetchone()
                            conn.close()
                            s_name = student[0] if student else "Unknown"
                            
                            # Broadcast WebSocket event to instantly update the UI table
                            socketio.emit('new_attendance', {
                                'roll': roll,
                                'name': s_name,
                                'time': time.strftime("%H:%M:%S"),
                                'confidence': conf
                            })

                        tracking["hits"][roll] += 1
                        msg = f"{s_name} - {time.strftime('%H:%M')} ({conf}% Match)"
                        if msg not in tracking["log"]: tracking["log"].append(msg)
                        
                    # If someone new walked into frame, broadcast a stats trigger to update UI Cards instantly
                    if new_detections:
                        socketio.emit('stats_update', {'trigger': True})
                        
                except: pass
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        cap.release()
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ==========================================
# REAL-TIME REST APIs
# ==========================================
@app.route('/api/live_stats')
def api_live_stats():
    """Returns JSON payload representing the current active Dashboard metrics."""
    if not tracking["active"]:
        return jsonify({"present": 0, "absent": 0, "percentage": 0, "active": False})
        
    present_count = 0
    # Determine who is currently present based on >= 50% frame validation threshold
    if tracking["total_checks"] > 0:
        for count in tracking["hits"].values():
            if (count / tracking["total_checks"]) * 100 >= 50:
                present_count += 1
                
    # Calculate Absents based on total enrolled students
    conn = sqlite3.connect("attendance.db")
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] or 0
    conn.close()
    
    absent_count = max(0, total_students - present_count)
    percentage = int((present_count / total_students * 100)) if total_students > 0 else 0
    
    return jsonify({
        "present": present_count,
        "absent": absent_count,
        "percentage": percentage,
        "active": True
    })

@app.route('/api/hardware_display')
def api_hardware_display():
    """Lightweight JSON API for ESP8266/ESP32 Arduino TFTs to poll locally."""
    if not tracking["active"]:
        return jsonify({
            "subject": "System Idle",
            "teacher": "Waiting...",
            "time": time.strftime("%H:%M"),
            "present_count": 0
        })

    # Instantly calculate current present humans identically to live stats
    present_count = 0
    if tracking["total_checks"] > 0:
        for count in tracking["hits"].values():
            if (count / tracking["total_checks"]) * 100 >= 50:
                present_count += 1
                
    return jsonify({
        "subject": tracking.get("subject", "Class"),
        "teacher": "Active",
        "time": time.strftime("%H:%M:%S"),
        "present_count": present_count
    })

@app.route('/analysis')
def analysis():
    conn = sqlite3.connect("attendance.db")
    
    # Line Chart (Trend)
    trend_data = conn.execute("SELECT date, COUNT(*) FROM attendance_logs WHERE status='PRESENT' GROUP BY date").fetchall()
    labels = [row[0] for row in trend_data] if trend_data else [time.strftime("%Y-%m-%d")]
    values = [row[1] for row in trend_data] if trend_data else [0]
    
    # Bar Chart (Subject)
    subject_data = conn.execute("SELECT subject, COUNT(*) FROM attendance_logs WHERE status='PRESENT' GROUP BY subject").fetchall()
    subject_labels = [row[0] for row in subject_data] if subject_data else ['General']
    subject_values = [row[1] for row in subject_data] if subject_data else [0]
    
    # Pie Chart (Status Distribution)
    status_data = conn.execute("SELECT status, COUNT(*) FROM attendance_logs GROUP BY status").fetchall()
    status_labels = [row[0] for row in status_data] if status_data else ['PRESENT', 'ABSENT']
    status_values = [row[1] for row in status_data] if status_data else [0, 0]
    
    # Cards Data
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] or 0
    total_logs = conn.execute("SELECT COUNT(*) FROM attendance_logs").fetchone()[0] or 1
    total_present = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE status='PRESENT'").fetchone()[0] or 0
    
    avg_attendance = int((total_present / total_logs) * 100) if total_logs > 0 else 0
    peak_date = labels[values.index(max(values))] if values else time.strftime("%Y-%m-%d")
    
    conn.close()
    
    return render_template(
        'analysis.html', 
        labels=labels, values=values,
        subject_labels=subject_labels, subject_values=subject_values,
        status_labels=status_labels, status_values=status_values,
        avg_attendance=avg_attendance, peak_date=peak_date, total_students=total_students
    )

@app.route('/api/chart_data', methods=['GET'])
def api_chart_data():
    conn = sqlite3.connect("attendance.db")
    # Trend
    t_data = conn.execute("SELECT date, COUNT(*) FROM attendance_logs WHERE status='PRESENT' GROUP BY date ORDER BY date ASC LIMIT 7").fetchall()
    # Subject
    sub_data = conn.execute("SELECT subject, COUNT(*) FROM attendance_logs WHERE status='PRESENT' GROUP BY subject").fetchall()
    # Status
    stat_data = conn.execute("SELECT status, COUNT(*) FROM attendance_logs GROUP BY status").fetchall()
    # Metrics
    total_studs = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] or 0
    total_logs = conn.execute("SELECT COUNT(*) FROM attendance_logs").fetchone()[0] or 1
    total_pres = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE status='PRESENT'").fetchone()[0] or 0
    
    vals = [row[1] for row in t_data] if t_data else [0]
    labels = [row[0] for row in t_data] if t_data else [time.strftime("%Y-%m-%d")]
    
    conn.close()
    return jsonify({
        'trend': {
            'labels': labels, 
            'values': vals
        },
        'subject': {
            'labels': [row[0] for row in sub_data] if sub_data else ['General'], 
            'values': [row[1] for row in sub_data] if sub_data else [0]
        },
        'status': {
            'labels': [row[0] for row in stat_data] if stat_data else ['PRESENT', 'ABSENT'], 
            'values': [row[1] for row in stat_data] if stat_data else [0, 0]
        },
        'metrics': {
            'avg_attendance': int((total_pres / total_logs) * 100) if total_logs > 0 else 0,
            'peak_date': labels[vals.index(max(vals))] if vals else time.strftime("%Y-%m-%d"),
            'total_students': total_studs
        }
    })

@app.route('/capture_photos', methods=['POST'])
def capture_photos():
    roll, name, s_class = request.form.get('roll'), request.form.get('name'), request.form.get('class')
    path = os.path.join(BASE_DIR, "dataset", roll)
    os.makedirs(path, exist_ok=True)
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    for i in range(10):
        ret, frame = cam.read()
        if ret: cv2.imwrite(f"{path}/{i}.jpg", frame)
        time.sleep(0.1)
    cam.release()
    conn = sqlite3.connect("attendance.db")
    conn.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (roll, name, s_class))
    conn.commit(); conn.close()
    return redirect(url_for('enroll', success='true'))

@app.route('/auth', methods=['POST'])
def authenticate():
    emp_id, password = request.form.get('emp_id'), request.form.get('password')
    conn = sqlite3.connect("attendance.db"); conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM faculty WHERE emp_id = ?", (emp_id,)).fetchone(); conn.close()
    if user and check_password_hash(user['password'], password):
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    return "Invalid Credentials"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        emp_id, password = request.form.get('emp_id'), request.form.get('password')
        conn = sqlite3.connect("attendance.db")
        conn.execute("INSERT INTO faculty VALUES (?, ?)", (emp_id, generate_password_hash(password)))
        conn.commit(); conn.close()
        return redirect(url_for('gatekeeper'))
    return render_template('signup.html')

@app.route('/enroll')
def enroll(): return render_template('register_student.html')

@app.route('/records')
def records():
    conn = sqlite3.connect("attendance.db"); conn.row_factory = sqlite3.Row
    logs = conn.execute("SELECT attendance_logs.*, students.name FROM attendance_logs LEFT JOIN students ON attendance_logs.roll = students.roll ORDER BY id DESC").fetchall(); conn.close()
    return render_template('records.html', logs=logs)

@app.route('/delete_log/<int:log_id>')
def delete_log(log_id):
    conn = sqlite3.connect("attendance.db"); conn.execute("DELETE FROM attendance_logs WHERE id = ?", (log_id,)); conn.commit(); conn.close()
    return redirect(url_for('records'))

@app.route('/settings')
def app_settings():
    if not session.get('logged_in'): return redirect('/')
    return render_template('settings.html')

@app.route('/export_csv')
def export_csv():
    conn = sqlite3.connect("attendance.db"); cursor = conn.execute("SELECT * FROM attendance_logs")
    file_path = os.path.join(BASE_DIR, "attendance_report.csv")
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['ID', 'Roll', 'Subject', 'Date', 'Status']); writer.writerows(cursor.fetchall())
    conn.close(); return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    # Execute via SocketIO wrapper to support WebSocket lifecycle
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
