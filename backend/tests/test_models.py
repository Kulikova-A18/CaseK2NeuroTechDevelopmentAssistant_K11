"""
Tests for Pydantic models and validation.
"""

import unittest
from datetime import datetime
from modules.models import UserCreate, TaskCreate, TaskUpdate, AuthRequest, LLMAnalysisRequest


class TestModels(unittest.TestCase):
    """Test Pydantic models."""
    
    def test_user_create_valid(self):
        """Test valid user creation."""
        user_data = {
            'telegram_username': '@testuser',
            'full_name': 'Test User',
            'role': 'member',
            'email': 'test@example.com'
        }
        
        user = UserCreate(**user_data)
        self.assertEqual(user.telegram_username, '@testuser')
        self.assertEqual(user.role, 'member')
    
    def test_user_create_invalid_telegram(self):
        """Test invalid Telegram username."""
        user_data = {
            'telegram_username': 'invalid',  # Missing @
            'full_name': 'Test User'
        }
        
        with self.assertRaises(ValueError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_role(self):
        """Test invalid user role."""
        user_data = {
            'telegram_username': '@testuser',
            'full_name': 'Test User',
            'role': 'invalid_role'  # Invalid role
        }
        
        with self.assertRaises(ValueError):
            UserCreate(**user_data)
    
    def test_task_create_valid(self):
        """Test valid task creation."""
        task_data = {
            'title': 'Test Task',
            'description': 'Test description',
            'status': 'todo',
            'priority': 'medium',
            'due_date': '2024-12-31',
            'tags': ['test', 'important']
        }
        
        task = TaskCreate(**task_data)
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.status, 'todo')
        self.assertEqual(task.due_date, '2024-12-31')
    
    def test_task_create_invalid_status(self):
        """Test invalid task status."""
        task_data = {
            'title': 'Test Task',
            'status': 'invalid_status',  # Invalid status
            'priority': 'medium'
        }
        
        with self.assertRaises(ValueError):
            TaskCreate(**task_data)
    
    def test_task_create_invalid_date(self):
        """Test invalid due date format."""
        task_data = {
            'title': 'Test Task',
            'status': 'todo',
            'priority': 'medium',
            'due_date': '31-12-2024'  # Wrong format
        }
        
        with self.assertRaises(ValueError):
            TaskCreate(**task_data)
    
    def test_task_update_partial(self):
        """Test partial task update."""
        update_data = {
            'title': 'Updated Title',
            'status': 'done'
        }
        
        task_update = TaskUpdate(**update_data)
        self.assertEqual(task_update.title, 'Updated Title')
        self.assertEqual(task_update.status, 'done')
        self.assertIsNone(task_update.description)  # Not provided
    
    def test_auth_request(self):
        """Test authentication request."""
        auth_data = {
            'telegram_username': '@testuser',
            'full_name': 'Test User'
        }
        
        auth_request = AuthRequest(**auth_data)
        self.assertEqual(auth_request.telegram_username, '@testuser')
        self.assertEqual(auth_request.full_name, 'Test User')
    
    def test_llm_analysis_request(self):
        """Test LLM analysis request."""
        llm_data = {
            'time_period': 'last_week',
            'metrics': ['productivity', 'bottlenecks'],
            'include_recommendations': True
        }
        
        llm_request = LLMAnalysisRequest(**llm_data)
        self.assertEqual(llm_request.time_period, 'last_week')
        self.assertIn('productivity', llm_request.metrics)
        self.assertTrue(llm_request.include_recommendations)
    
    def test_llm_analysis_invalid_metric(self):
        """Test LLM analysis with invalid metric."""
        llm_data = {
            'time_period': 'last_week',
            'metrics': ['invalid_metric'],  # Invalid metric
            'include_recommendations': True
        }
        
        with self.assertRaises(ValueError):
            LLMAnalysisRequest(**llm_data)


if __name__ == '__main__':
    unittest.main()