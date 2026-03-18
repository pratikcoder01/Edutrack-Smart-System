import os, cv2, time, requests
from flask import Flask, Response
from flask_cors import CORS
from recognizer import get_present_rolls

# Initialize local Flask for video streaming to the Vercel Dashboard
app = Flask(__name__)
CORS(app) # Allow Vercel frontend to fetch video feed

# CHANGE THIS ONCE VERCEL IS DEPLOYED
# API_URL = "https://your-vercel-app.vercel.app/api/updateAttendance"
API_URL = "http://localhost:3000/api/updateAttendance" 

tracking = {"active": True, "hits": {}, "subject": "General"}

@app.route('/video_feed')
def video_feed():
    def gen():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            if tracking["active"]:
                try:
                    present_rolls = get_present_rolls(frame)
                    for match in present_rolls:
                        roll, conf = match if isinstance(match, tuple) else (match, 85)
                        
                        # Only send API request if we haven't flooded it (basic debounce)
                        if roll not in tracking["hits"] or (time.time() - tracking["hits"][roll]) > 10:
                            tracking["hits"][roll] = time.time()
                            
                            try:
                                # Post to Supabase via Vercel Serverless Function
                                response = requests.post(API_URL, json={
                                    "roll": roll,
                                    "confidence": conf,
                                    "subject": tracking["subject"]
                                }, timeout=2)
                                print(f"Sent {roll} ({conf}%). API Response:", response.status_code)
                            except Exception as api_err:
                                print("API Error:", api_err)
                except Exception as e: 
                    pass
                    
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        cap.release()
        
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def status():
    return {"status": "Scanner Active", "monitoring": tracking["active"]}

if __name__ == '__main__':
    print("Starting Local AI Scanner...")
    print(f"Targeting Vercel API: {API_URL}")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
