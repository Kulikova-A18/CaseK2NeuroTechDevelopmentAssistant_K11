"""
Tests for system constants and configuration.
"""

import unittest
from modules.constants import SystemConstants


class TestSystemConstants(unittest.TestCase):
    """Test system constants."""
    
    def test_roles(self):
        """Test user roles."""
        self.assertIn('admin', SystemConstants.ROLES)
        self.assertIn('member', SystemConstants.ROLES)
        self.assertEqual(len(SystemConstants.ROLES), 4)
    
    def test_task_statuses(self):
        """Test task statuses."""
        self.assertIn('todo', SystemConstants.TASK_STATUSES)
        self.assertIn('done', SystemConstants.TASK_STATUSES)
    
    def test_priorities(self):
        """Test task priorities."""
        self.assertIn('high', SystemConstants.TASK_PRIORITIES)
        self.assertIn('urgent', SystemConstants.TASK_PRIORITIES)
    
    def test_csv_paths(self):
        """Test CSV file paths."""
        self.assertIn('users', SystemConstants.CSV_PATHS)
        self.assertIn('tasks', SystemConstants.CSV_PATHS)
        self.assertTrue(SystemConstants.CSV_PATHS['users'].endswith('.csv'))
    
    def test_default_values(self):
        """Test default values."""
        self.assertEqual(SystemConstants.DEFAULT_SESSION_TIMEOUT_HOURS, 24)
        self.assertEqual(SystemConstants.DEFAULT_CACHE_TTL_SECONDS, 300)
    
    def test_websocket_events(self):
        """Test WebSocket events."""
        self.assertIn('TASK_CREATED', SystemConstants.WS_EVENTS)
        self.assertIn('USER_ONLINE', SystemConstants.WS_EVENTS)


if __name__ == '__main__':
    unittest.main()