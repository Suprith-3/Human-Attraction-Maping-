import os
import tempfile
import unittest
import json
import sqlite3
from unittest.mock import patch, MagicMock

# Import the Flask application and database module
from app import app
import database

class FocusOSTestCase(unittest.TestCase):
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

    def tearDown(self):
        # Close and unlink the temporary db
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_index_redirects_to_login(self):
        """Test if index page redirects to login when not authenticated."""
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 302)
        self.assertIn(b'/login', rv.data)

    def test_register_user(self):
        """Test user registration API."""
        rv = self.client.post('/api/auth/register', json={
            'name': 'Test User',
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Registration successful')

    def test_duplicate_register(self):
        """Test registration with existing email."""
        self.client.post('/api/auth/register', json={
            'name': 'User1', 'email': 'test@example.com', 'password': 'pw1'
        })
        rv = self.client.post('/api/auth/register', json={
            'name': 'User2', 'email': 'test@example.com', 'password': 'pw2'
        })
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertFalse(data['success'])

    def test_login_success(self):
        """Test logging in with correct credentials."""
        self.client.post('/api/auth/register', json={
            'name': 'Login User', 'email': 'login@example.com', 'password': 'mypassword'
        })
        
        rv = self.client.post('/api/auth/login', json={
            'email': 'login@example.com', 'password': 'mypassword'
        })
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertTrue(data['success'])

        with self.client.session_transaction() as sess:
            self.assertIn('user_id', sess)

    def test_login_failure(self):
        """Test logging in with incorrect credentials."""
        self.client.post('/api/auth/register', json={
            'name': 'Login User', 'email': 'login@example.com', 'password': 'mypassword'
        })
        
        rv = self.client.post('/api/auth/login', json={
            'email': 'login@example.com', 'password': 'wrongpassword'
        })
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertFalse(data['success'])
        
    def test_protected_routes(self):
        """Test that protected API routes return 401 when unauthenticated."""
        rv = self.client.post('/api/session/start')
        self.assertEqual(rv.status_code, 401)

    def test_session_tracking_flow(self):
        """Test the lifecycle of starting a session, tracking stats, and ending it."""
        # 1. Register and Login
        self.client.post('/api/auth/register', json={'name': 'Tracker', 'email': 'track@ex.com', 'password': 'pw'})
        self.client.post('/api/auth/login', json={'email': 'track@ex.com', 'password': 'pw'})

        # 2. Start Session
        rv = self.client.post('/api/session/start')
        self.assertEqual(rv.status_code, 200)
        session_data = json.loads(rv.data)
        self.assertIn('session_id', session_data)
        session_id = session_data['session_id']

        # 3. Track Keystrokes
        rv = self.client.post('/api/track/keys', json={'session_id': session_id, 'count': 42})
        self.assertEqual(rv.status_code, 200)

        # 4. End Session
        rv = self.client.post('/api/session/end', json={'session_id': session_id, 'tab_shifts': 3, 'idle_minutes': 5})
        self.assertEqual(rv.status_code, 200)

        # 5. Verify the data in DB directly
        conn = database.get_db()
        sess_record = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        conn.close()
        
        self.assertIsNotNone(sess_record)
        self.assertEqual(sess_record['keystrokes'], 42)
        # focus_score = max(0, 100 - (3 * 5) - 5) = 80
        self.assertEqual(sess_record['focus_score'], 80.0)

    @patch('cv_module.cv2.VideoCapture')
    def test_cv_toggle_start_stop(self, mock_videocapture):
        """Test turning the computer vision module on and off."""
        # Note: We mock VideoCapture so it doesn't open the real webcam.
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_videocapture.return_value = mock_cap
        
        self.client.post('/api/auth/register', json={'name': 'CV User', 'email': 'cv@ex.com', 'password': 'pw'})
        self.client.post('/api/auth/login', json={'email': 'cv@ex.com', 'password': 'pw'})
        
        # Start CV
        rv = self.client.post('/api/cv/toggle', json={'enabled': True})
        self.assertEqual(rv.status_code, 200)
        
        # Stop CV
        rv = self.client.post('/api/cv/toggle', json={'enabled': False})
        self.assertEqual(rv.status_code, 200)

if __name__ == '__main__':
    unittest.main()
