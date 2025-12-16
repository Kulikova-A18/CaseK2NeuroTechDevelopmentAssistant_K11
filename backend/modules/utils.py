"""
Utility functions and helpers.
Contains common utilities used across the system.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any

from modules.constants import SystemConstants


def initialize_sample_data(tasks_manager, users_manager):
    """
    Initialize sample system data.
    Creates example users and tasks for demonstration.
    
    @param tasks_manager: CSV data manager for tasks
    @param users_manager: CSV data manager for users
    """
    # Check if data already exists
    existing_users = users_manager.read_all()
    if len(existing_users) > 1:  # Account for header
        logging.info("Sample data already exists")
        return
    
    logging.info("Initializing sample data...")
    
    # Create sample users
    sample_users = [
        {
            'telegram_username': '@admin_ivan',
            'full_name': 'Иван Петров',
            'role': 'admin',
            'is_active': 'True',
            'email': 'ivan@company.com',
            'department': 'IT'
        },
        {
            'telegram_username': '@manager_anna',
            'full_name': 'Анна Сидорова',
            'role': 'manager',
            'is_active': 'True',
            'email': 'anna@company.com',
            'department': 'Project Management'
        },
        {
            'telegram_username': '@developer_alex',
            'full_name': 'Алексей Козлов',
            'role': 'member',
            'is_active': 'True',
            'email': 'alex@company.com',
            'department': 'Development'
        },
        {
            'telegram_username': '@viewer_olga',
            'full_name': 'Ольга Новикова',
            'role': 'viewer',
            'is_active': 'True',
            'email': 'olga@company.com',
            'department': 'Sales'
        }
    ]
    
    for user_data in sample_users:
        users_manager.insert(user_data)
    
    # Create sample tasks
    sample_tasks = [
        {
            'task_id': '101',
            'title': 'Разработка REST API',
            'description': 'Создать API endpoints для системы управления задачами',
            'status': 'in_progress',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'high',
            'tags': json.dumps(['backend', 'api', 'priority'], ensure_ascii=False)
        },
        {
            'task_id': '102',
            'title': 'Исправить критический баг',
            'description': 'Ошибка при сохранении данных в CSV',
            'status': 'done',
            'assignee': '@developer_alex',
            'creator': '@admin_ivan',
            'priority': 'urgent',
            'tags': json.dumps(['bug', 'critical', 'hotfix'], ensure_ascii=False)
        },
        {
            'task_id': '103',
            'title': 'Обновить документацию',
            'description': 'Добавить новые API методы в документацию',
            'status': 'todo',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'medium',
            'tags': json.dumps(['docs', 'api'], ensure_ascii=False)
        }
    ]
    
    for task_data in sample_tasks:
        tasks_manager.insert(task_data)
    
    logging.info("Sample data created successfully")