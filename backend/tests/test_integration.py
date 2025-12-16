"""
Integration tests for the complete system.
"""

import unittest
import json
import tempfile
import os
from datetime import datetime

# Mock Flask app for testing
from flask import Flask, jsonify
from flask.testing import FlaskClient


class TestIntegration(unittest.TestCase):
    """Integration tests for the system."""
    
    def setUp(self):
        """Set up test environment."""
        # This is a simplified integration test
        # In a real scenario, you'd use a test Flask app
        self.test_data_dir = tempfile.mkdtemp()
        
        # Create test CSV files
        self.users_csv = os.path.join(self.test_data_dir, 'users.csv')
        self.tasks_csv = os.path.join(self.test_data_dir, 'tasks.csv')
        
        # Write initial data
        with open(self.users_csv, 'w') as f:
            f.write('telegram_username,full_name,role,is_active\n')
            f.write('@testuser,Test User,member,True\n')
        
        with open(self.tasks_csv, 'w') as f:
            f.write('task_id,title,status,creator,priority\n')
            f.write('1,Test Task,todo,@testuser,medium\n')
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_data_dir)
    
    def test_sample_data_creation(self):
        """Test that sample data can be created."""
        from modules.csv_manager import CSVDataManager
        from modules.constants import SystemConstants
        
        # Modify paths for testing
        test_constants = type('TestConstants', (), {
            'USERS_SCHEMA': SystemConstants.USERS_SCHEMA,
            'TASKS_SCHEMA': SystemConstants.TASKS_SCHEMA,
            'CSV_PATHS': {
                'users': self.users_csv,
                'tasks': self.tasks_csv
            }
        })
        
        users_manager = CSVDataManager(
            test_constants.CSV_PATHS['users'],
            test_constants.USERS_SCHEMA
        )
        
        tasks_manager = CSVDataManager(
            test_constants.CSV_PATHS['tasks'],
            test_constants.TASKS_SCHEMA
        )
        
        # Test reading existing data
        users = users_manager.read_all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['telegram_username'], '@testuser')
        
        tasks = tasks_manager.read_all()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['title'], 'Test Task')
        
        # Test creating new task
        new_task = {
            'task_id': '2',
            'title': 'New Task',
            'status': 'in_progress',
            'creator': '@testuser',
            'priority': 'high'
        }
        
        tasks_manager.insert(new_task)
        
        # Verify new task
        tasks = tasks_manager.read_all()
        self.assertEqual(len(tasks), 2)
        
        # Find new task
        new_task_found = tasks_manager.find_one(task_id='2')
        self.assertEqual(new_task_found['title'], 'New Task')
    
    def test_json_validation(self):
        """Test JSON serialization/deserialization for tags."""
        import json
        
        # Test JSON serialization
        tags = ['backend', 'api', 'priority']
        json_tags = json.dumps(tags, ensure_ascii=False)
        
        # Test JSON deserialization
        parsed_tags = json.loads(json_tags)
        self.assertEqual(parsed_tags, tags)
        self.assertIn('api', parsed_tags)
    
    def test_datetime_formatting(self):
        """Test datetime formatting for CSV."""
        from datetime import datetime
        
        # Test formatting
        now = datetime.now()
        formatted = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # Should match expected format
        self.assertRegex(formatted, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        
        # Test parsing
        parsed = datetime.strptime(formatted, '%Y-%m-%d %H:%M:%S')
        self.assertEqual(parsed.year, now.year)
        self.assertEqual(parsed.month, now.month)
        self.assertEqual(parsed.day, now.day)


if __name__ == '__main__':
    unittest.main()