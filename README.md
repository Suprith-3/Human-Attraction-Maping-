# 🎯 FocusOS: The Ultimate Local-First Privacy-Focused Productivity System

FocusOS is a state-of-the-art, 100% offline productivity tracker designed to help you reclaim your deep work. It uses advanced computer vision and interaction analytics to visualize your attention without ever sending a single pixel of your data to the cloud.

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Backend](https://img.shields.io/badge/backend-Flask-lightgrey)
![Offline](https://img.shields.io/badge/PWA-Offline--First-orange)

---

## 🚀 Key Features

### 🧩 Attention Analytics
- **Neon Gravity Map**: A high-tech tactical visualization of your mouse attention patterns across the screen.
- **Distribution Wheel**: Real-time breakdown of your keyboard, mouse, and switching activity.
- **Live Interaction Bar**: Track your keystrokes, clicks, and mouse travel distance (cm) in real-time.

### 🛡️ Adaptive Shielding
- **Forceful Adaptive Blocking**: Detects excessive context switching (3 shifts in 2 mins) and **locks your cursor and keyboard** using the Pointer Lock API.
- **Focus Lock**: Hard-lock yourself into a specific application or URL.

### 👁️ AI Watchdog (Computer Vision)
- **Face & Alertness Detection**: Uses OpenCV to detect if you look away or if your head bends (fatigue).
- **The "Dog Barking" Alert**: Triggers a unique synthesized "Dog Bark" sound effect when focus is broken to pull you back into the zone instantly.

### 🪙 Gamified Rewards
- **Focus Coins**: Earn currency based on session performance and streaks.
- **Theme Store**: Unlock premium UI themes (Neon, Ocean, Sunset) using earned coins.
- **Badge System**: Collect badges for milestones like "Deep Work Master" or "Switch Slayer."

### 🌐 Zero-Connection Required
- **PWA Ready**: Install as a standalone desktop/mobile app.
- **Offline Sync**: All data is queued locally and synced to the SQLite database automatically.

---

## 🛠️ Technology Stack
- **Backend:** Python, Flask
- **Database:** SQLite (local-only)
- **Security:** Bcrypt hashing
- **Computer Vision:** OpenCV + Haar Cascades
- **Aesthetics:** Vanilla CSS (Glassmorphism + Dark Mode)
- **Frontend:** Plain JavaScript (ES6+), Chart.js, Heatmap.js

---

## 🏁 Getting Started

### Prerequisites
- Python 3.8 or higher
- A working webcam (for AI detection features)

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/focusos.git
   cd focusos
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the Dashboard:**
   Open your browser and navigate to `http://localhost:5000`

---

## 📋 How to Use
1. **Register/Login**: Since it's local-first, your data stays on your machine.
2. **Start Session**: Click "Start Session" in the top bar to begin tracking interaction metrics.
3. **Engagement Targets**: Set a goal app (e.g., VS Code) and a timer. FocusOS will bark if you switch tabs.
4. **Adaptive Blocking**: Toggle this on in the "Controls" tab to prevent yourself from mindless browsing.
5. **View Results**: End your session to save data and see your Heatmaps and Gravity Map in the Analytics tab.

---

## 🔒 Privacy Guarantee
FocusOS is built on a strictly **"No Data Leaves the Device"** policy.
- No screen recording.
- No text capture or keylogging of content.
- No internet connection required for core tracking features.
- All CV processing happens on your local CPU.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
