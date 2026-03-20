import cv2, threading, time
from database import log_cv_alert

class AttentionDetector:
    def __init__(self):
        self.running = False
        self.thread = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.no_eyes_start = None
        self.alert_callback = None

    def start(self, user_id, alert_callback):
        self.running = True
        self.user_id = user_id
        self.alert_callback = alert_callback
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        cap = cv2.VideoCapture(0)
        while self.running:
            ret, frame = cap.read()
            if not ret: continue
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

            # Check if person is concentrating (detected face + eyes)
            distracted = False
            alert_type = 'no_face'

            if len(faces) == 0:
                distracted = True
                alert_type = 'no_face'
            else:
                # Look for eyes within face
                for (x, y, w, h) in faces:
                    roi_gray = gray[y:y+h, x:x+w]
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 3)
                    
                    if len(eyes) < 1:
                        distracted = True
                        alert_type = 'no_eyes'
                        break
                    
                    # Check for head turn: if face is too narrow/tall compared to average
                    ratio = h / w
                    if ratio > 1.4:
                        self.alert_callback(self.user_id, 'head_bend')
            
            if distracted:
                if self.no_eyes_start is None:
                    self.no_eyes_start = time.time()
                elif time.time() - self.no_eyes_start >= 2:
                    self.alert_callback(self.user_id, alert_type)
                    self.no_eyes_start = None
            else:
                self.no_eyes_start = None

            time.sleep(0.5)
        cap.release()
