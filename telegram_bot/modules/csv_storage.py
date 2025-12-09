import csv
import os
import time

USERS_CSV = 'users.csv'
TASKS_CSV = 'tasks.csv'

def init_csv_files():
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'user_id', 'telegram_user_id', 'telegram_username', 'full_name',
                'registration_timestamp', 'last_login', 'is_active', 'role'
            ])
            writer.writeheader()
            writer.writerow({
                'user_id': 1,
                'telegram_user_id': 123456789,
                'telegram_username': 'alyona',
                'full_name': 'Алёна Куликова',
                'registration_timestamp': '2025-12-10 10:00:00',
                'last_login': '2025-12-10 10:00:00',
                'is_active': 'True',
                'role': 'admin'
            })

    if not os.path.exists(TASKS_CSV):
        with open(TASKS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'task_id', 'title', 'description', 'status', 'assignee_user_id',
                'creator_user_id', 'created_at', 'updated_at', 'due_date',
                'completed_at', 'priority', 'tags'
            ])
            writer.writeheader()
            writer.writerow({
                'task_id': 1,
                'title': 'Финализировать логику бота',
                'description': 'Добавить управление пользователями',
                'status': 'in_progress',
                'assignee_user_id': 1,
                'creator_user_id': 1,
                'created_at': '2025-12-10 10:00:00',
                'updated_at': '2025-12-10 10:00:00',
                'due_date': '2025-12-20 23:59:59',
                'completed_at': '',
                'priority': 'high',
                'tags': '["бот", "админка"]'
            })

    from .invite_manager import init_invites_file
    init_invites_file()

def load_data():
    users_by_username = {}
    users_by_id = {}
    tasks = {}

    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                tid = int(row['telegram_user_id'])
                username = row['telegram_username'].lower() if row['telegram_username'] else None
                row['is_active'] = row['is_active'] == 'True'
                row['user_id'] = int(row['user_id'])
                if username:
                    users_by_username[username] = row
                users_by_id[tid] = row

    if os.path.exists(TASKS_CSV):
        with open(TASKS_CSV, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                tid = int(row['task_id'])
                row['task_id'] = tid
                row['assignee_user_id'] = int(row['assignee_user_id']) if row['assignee_user_id'] else None
                row['creator_user_id'] = int(row['creator_user_id'])
                tasks[tid] = row

    return users_by_username, users_by_id, tasks

def save_users(users_by_id):
    with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'user_id', 'telegram_user_id', 'telegram_username', 'full_name',
            'registration_timestamp', 'last_login', 'is_active', 'role'
        ])
        writer.writeheader()
        for user in users_by_id.values():
            writer.writerow({
                'user_id': user['user_id'],
                'telegram_user_id': user['telegram_user_id'],
                'telegram_username': user['telegram_username'],
                'full_name': user['full_name'],
                'registration_timestamp': user['registration_timestamp'],
                'last_login': user['last_login'],
                'is_active': str(user['is_active']),
                'role': user['role']
            })

def save_tasks(tasks):
    with open(TASKS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'task_id', 'title', 'description', 'status', 'assignee_user_id',
            'creator_user_id', 'created_at', 'updated_at', 'due_date',
            'completed_at', 'priority', 'tags'
        ])
        writer.writeheader()
        for task in tasks.values():
            writer.writerow(task)