import os

app_path = r"c:\Users\Pratik\Downloads\Edutrack-Smart-System\Edutrack-Smart-system\app.py"
with open(app_path, "r", encoding="utf-8") as f:
    app_text = f.read()

app_text = app_text.replace(
'''                            socketio.emit('new_attendance', {
                                'roll': roll,
                                'name': s_name,
                                'time': time.strftime("%H:%M:%S")
                            })''',
'''                            socketio.emit('new_attendance', {
                                'roll': roll,
                                'name': s_name,
                                'time': time.strftime("%H:%M:%S"),
                                'confidence': conf
                            })'''
)

app_text = app_text.replace(
'''                        tracking["hits"][roll] += 1
                        msg = f"Detected: {roll}"
                        if msg not in tracking["log"]: tracking["log"].append(msg)''',
'''                        tracking["hits"][roll] += 1
                        msg = f"{s_name} - {time.strftime('%H:%M')} ({conf}% Match)"
                        if msg not in tracking["log"]: tracking["log"].append(msg)'''
)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(app_text)


dash_path = r"c:\Users\Pratik\Downloads\Edutrack-Smart-System\Edutrack-Smart-system\frontend\templates\dashboard.html"
with open(dash_path, "r", encoding="utf-8") as f:
    dash_text = f.read()

dash_text = dash_text.replace(
'''                <td class="text-muted small">${data.time}</td>
                <td><span class="badge-status badge-present">Present</span></td>''',
'''                <td class="text-muted small">${data.time}</td>
                <td>
                    <span class="badge-status badge-present">Present</span>
                    <span class="ms-2 small fw-bold text-${data.confidence >= 70 ? 'success' : 'warning'}">${data.confidence}% Match</span>
                </td>'''
)

with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash_text)
