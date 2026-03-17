import cv2, threading, time
from database import log_cv_alert

class AttentionDetector:
    def __init__(self):
        self.running = False
        self.thread = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.no_face_start = None
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

            if len(faces) == 0:
                if self.no_face_start is None:
                    self.no_face_start = time.time()
                elif time.time() - self.no_face_start >= 2:
                    self.alert_callback(self.user_id, 'no_face')
                    self.no_face_start = None
            else:
                self.no_face_start = None
                # Check for head bend: if face bounding box height > width * 1.5
                for (x, y, w, h) in faces:
                    if h > w * 1.5:
                        self.alert_callback(self.user_id, 'head_bend')

            time.sleep(0.5)
        cap.release()
