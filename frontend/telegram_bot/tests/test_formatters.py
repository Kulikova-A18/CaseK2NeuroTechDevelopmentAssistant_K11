"""
Tests for message formatters.
"""

import json
from modules.formatters import MessageFormatter
from modules.constants import BotConstants


def test_format_task():
    """Test task formatting."""
    task = {
        'task_id': 1,
        'title': 'Test Task',
        'description': 'This is a test task description that is quite long',
        'assignee': '@testuser',
        'creator': '@admin',
        'status': 'todo',
        'priority': 'high',
        'created_at': '2024-01-01T10:00:00Z',
        'due_date': '2024-01-15',
        'days_remaining': 5,
        'tags': ['test', 'urgent']
    }
    
    formatted = MessageFormatter.format_task(task)
    
    assert 'Задача #1' in formatted
    assert 'Заголовок: Test Task' in formatted
    assert 'Описание:' in formatted
    assert 'Назначена: @testuser' in formatted
    assert 'Статус: To Do' in formatted
    assert 'Приоритет: Высокий' in formatted
    assert 'Дедлайн: 2024-01-15 (осталось 5 дней)' in formatted
    assert 'Теги: #test #urgent' in formatted


def test_format_task_no_description():
    """Test task formatting without description."""
    task = {
        'task_id': 2,
        'title': 'Simple Task',
        'assignee': '@user',
        'status': 'in_progress',
        'priority': 'medium'
    }
    
    formatted = MessageFormatter.format_task(task)
    
    assert 'Задача #2' in formatted
    assert 'Заголовок: Simple Task' in formatted
    assert 'Описание:' not in formatted
    assert 'Статус: In Progress' in formatted
    assert 'Приоритет: Средний' in formatted


def test_format_task_overdue():
    """Test task formatting for overdue task."""
    task = {
        'task_id': 3,
        'title': 'Overdue Task',
        'status': 'todo',
        'priority': 'urgent',
        'due_date': '2024-01-01',
        'days_remaining': -3
    }
    
    formatted = MessageFormatter.format_task(task)
    
    assert 'Дедлайн: Просрочено на 3 дней' in formatted
    assert 'Приоритет: Срочный' in formatted


def test_format_tasks_list():
    """Test tasks list formatting."""
    tasks = [
        {
            'task_id': 1,
            'title': 'First Task',
            'assignee': '@user1',
            'status': 'todo',
            'priority': 'low'
        },
        {
            'task_id': 2,
            'title': 'Second Task with Very Long Title That Should Be Truncated',
            'assignee': '@user2',
            'status': 'in_progress',
            'priority': 'high',
            'due_date': '2024-01-02',
            'days_remaining': 0
        }
    ]
    
    formatted = MessageFormatter.format_tasks_list(tasks)
    
    assert 'Найдено задач: 2' in formatted
    assert '#1 - First Task' in formatted
    assert '#2 - Second Task with Very Long Title' in formatted
    assert '@user1' in formatted
    assert '(t/l)' in formatted.lower() or '(t/н)' in formatted.lower()  # todo/low
    assert '[Сегодня]' in formatted


def test_format_tasks_list_empty():
    """Test empty tasks list formatting."""
    formatted = MessageFormatter.format_tasks_list([])
    assert formatted == "Задачи не найдены"


def test_format_tasks_list_many_tasks():
    """Test formatting with many tasks (more than limit)."""
    tasks = [{'task_id': i, 'title': f'Task {i}', 'assignee': '@user', 'status': 'todo', 'priority': 'medium'} 
             for i in range(20)]
    
    formatted = MessageFormatter.format_tasks_list(tasks)
    
    assert 'Найдено задач: 20' in formatted
    assert 'Показаны первые 15 задач' in formatted
    assert 'Для просмотра всех задач используйте экспорт' in formatted
    assert '... и еще 5 задач' in formatted


def test_format_user_info():
    """Test user info formatting."""
    user_info = {
        'user': {
            'full_name': 'Test User',
            'telegram_username': '@testuser',
            'role': 'admin',
            'is_active': 'true',
            'email': 'test@example.com',
            'department': 'IT',
            'last_login': '2024-01-01 10:00:00'
        },
        'permissions': {
            'can_create_tasks': True,
            'can_edit_tasks': True,
            'can_delete_tasks': True,
            'can_export': True,
            'can_use_llm': True,
            'can_manage_users': True,
            'llm_daily_limit': 10
        }
    }
    
    formatted = MessageFormatter.format_user_info(user_info)
    
    assert 'Ваш профиль' in formatted
    assert 'Имя: Test User' in formatted
    assert 'Telegram: @testuser' in formatted
    assert 'Роль: Admin' in formatted
    assert 'Статус: Активен' in formatted
    assert 'Email: test@example.com' in formatted
    assert 'Отдел: IT' in formatted
    assert 'Права доступа:' in formatted
    assert '- Создавать задачи' in formatted
    assert '- Редактировать задачи' in formatted
    assert '- Использовать AI анализ' in formatted
    assert 'Лимит AI запросов: 10/день' in formatted
    assert 'Последний вход: 2024-01-01 10:00:00' in formatted


def test_format_user_info_minimal():
    """Test user info formatting with minimal data."""
    user_info = {
        'user': {
            'full_name': 'Minimal User',
            'telegram_username': '@minimal',
            'role': 'member',
            'is_active': 'false'
        },
        'permissions': {}
    }
    
    formatted = MessageFormatter.format_user_info(user_info)
    
    assert 'Имя: Minimal User' in formatted
    assert 'Telegram: @minimal' in formatted
    assert 'Роль: Member' in formatted
    assert 'Статус: Неактивен' in formatted
    assert 'Email:' not in formatted  # Should not be present
    assert 'Лимит AI запросов: 0/день' in formatted


def test_format_user_info_empty():
    """Test user info formatting with empty data."""
    formatted = MessageFormatter.format_user_info({})
    assert formatted == "Информация о пользователе недоступна"