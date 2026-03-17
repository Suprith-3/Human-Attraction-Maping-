import os
import tempfile
import unittest
import json
import sqlite3

# Import the Flask application and database module
from app import app
import database

class FocusOSUITestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for isolation
        self.db_fd, self.db_path = tempfile.mkstemp()
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Override the actual DB_PATH with the temporary one
        database.DB_PATH = self.db_path
        
        # Re-initialize the test database schema
        with app.app_context():
            database.init_db()

        # Register and login a dummy user for UI/UX testing
        self.client.post('/api/auth/register', json={
            'name': 'UI Tester',
            'email': 'tester@example.com',
            'password': 'testpassword'
        })
        self.client.post('/api/auth/login', json={
            'email': 'tester@example.com',
            'password': 'testpassword'
        })

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_dashboard_ui_tabs_presence(self):
        """Test if the Dashboard UX correctly renders all sidebar tabs for navigation."""
        rv = self.client.get('/dashboard')
        self.assertEqual(rv.status_code, 200)
        html = rv.data.decode('utf-8')
        
        # Check for UI Tab Buttons
        self.assertIn("switchTab('overview')", html)
        self.assertIn("switchTab('gravity')", html)
        self.assertIn("switchTab('engage')", html)
        self.assertIn("switchTab('history')", html)
        self.assertIn("switchTab('rewards')", html)
        self.assertIn("switchTab('controls')", html)

    def test_ux_overlays_presence(self):
        """Test if vital UX overlay elements (Focus Lock, Adaptive Lock) are in the DOM."""
        rv = self.client.get('/dashboard')
        html = rv.data.decode('utf-8')

        self.assertIn('id="adaptive-lock-overlay"', html, "Adaptive lock UX missing")
        self.assertIn('id="focus-lock-overlay"', html, "Focus lock UX missing")
        self.assertIn('id="flash-overlay"', html, "Flash overlay UX missing")
        self.assertIn('id="connection-pill"', html, "Online status pill missing")

    def test_history_ui_structure(self):
        """Test if the UI correctly defines the History table for JavaScript rendering."""
        rv = self.client.get('/dashboard')
        html = rv.data.decode('utf-8')

        # Check for history tab container
        self.assertIn('id="history-tab"', html)
        # Check table structure
        self.assertIn('id="history-table"', html)
        self.assertIn('<th>Date</th>', html)
        self.assertIn('<th>Keys</th>', html)
        self.assertIn('<th>Clicks</th>', html)
        self.assertIn('<th>Score</th>', html)

    def test_history_api_output(self):
        """Test the exact output data payload that feeds the History UI."""
        # 1. Start a session
        rv_start = self.client.post('/api/session/start')
        session_id = json.loads(rv_start.data)['session_id']

        # 2. Simulate User output actions
        self.client.post('/api/track/keys', json={'session_id': session_id, 'count': 120})
        self.client.post('/api/track/mouse', json={'session_id': session_id, 'clicks': 25, 'actions': 50})
        self.client.post('/api/track/tabs', json={'session_id': session_id, 'shift_count': 2})
        self.client.post('/api/track/path', json={'session_id': session_id, 'total_pixels': 1500, 'total_cm': 50.5})

        # 3. End the session (this calculates the focus score)
        self.client.post('/api/session/end', json={
            'session_id': session_id, 
            'tab_shifts': 2, 
            'idle_minutes': 1
        })

        # 4. Fetch History Output
        rv_history = self.client.get('/api/stats/history')
        self.assertEqual(rv_history.status_code, 200)
        history_data = json.loads(rv_history.data)

        # 5. Validate output structure and accuracy
        self.assertTrue(len(history_data) > 0)
        latest_session = history_data[0]
        
        # Verify accurate metric outputs
        self.assertEqual(latest_session['keystrokes'], 120)
        self.assertEqual(latest_session['clicks'], 25)
        self.assertEqual(latest_session['tab_shifts'], 2)
        self.assertEqual(latest_session['mouse_cm'], 50.5)
        
        # base 100 - (2 shifts * 5) - 1 idle = 89
        self.assertEqual(latest_session['focus_score'], 89.0)

    def test_realtime_ux_outputs(self):
        """Test the real-time API output that feeds Dashboard Charts."""
        rv = self.client.get('/api/stats/realtime')
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)

        # Output must contain timeline structure for 60 iterations (1 hour)
        self.assertIn('labels', data)
        self.assertIn('keystrokes', data)
        self.assertEqual(len(data['labels']), 60)
        self.assertEqual(len(data['keystrokes']), 60)

if __name__ == '__main__':
    unittest.main()
