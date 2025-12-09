import time
from .csv_storage import save_tasks, save_users

def handle_task_command(task_id, tasks, users_by_username):
    task = tasks.get(task_id)
    if not task:
        return f"Задача с ID {task_id} не найдена."
    assignee_name = "Не назначен"
    if task['assignee_user_id']:
        for u in users_by_username.values():
            if u['user_id'] == task['assignee_user_id']:
                assignee_name = u['full_name'] or u['telegram_username']
                break
    return (
        f"<b>Задача #{task_id}</b>\n"
        f"<b>Название:</b> {task['title']}\n"
        f"<b>Статус:</b> <code>{task['status']}</code>\n"
        f"<b>Исполнитель:</b> {assignee_name}\n"
        f"<b>Приоритет:</b> {task['priority']}\n"
        f"<b>Описание:</b> {task['description'] or '—'}\n"
        f"<b>Срок:</b> {task['due_date'] or '—'}"
    )

def handle_set_status_command(task_id, new_status, tasks, telegram_username):
    if new_status not in ['todo', 'in_progress', 'done']:
        return "Недопустимый статус."
    if task_id not in tasks:
        return f"Задача #{task_id} не найдена."
    tasks[task_id]['status'] = new_status
    tasks[task_id]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    if new_status == 'done':
        tasks[task_id]['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        tasks[task_id]['completed_at'] = ''
    save_tasks(tasks)
    return f"Статус задачи #{task_id} успешно обновлён на «{new_status}»."

def handle_list_tasks(tasks, users_by_username):
    if not tasks:
        return "Нет задач."
    lines = ["<b>Список всех задач:</b>\n"]
    for task in tasks.values():
        assignee = "Не назначен"
        if task['assignee_user_id']:
            for u in users_by_username.values():
                if u['user_id'] == task['assignee_user_id']:
                    assignee = u['full_name'] or u['telegram_username']
                    break
        lines.append(
            f"• №{task['task_id']} — <b>{task['title']}</b>\n"
            f"  Статус: <code>{task['status']}</code>, Исполнитель: {assignee}"
        )
    return "\n\n".join(lines)

def handle_list_users(users_by_username):
    if not users_by_username:
        return "Нет зарегистрированных пользователей."
    lines = ["<b>Зарегистрированные пользователи:</b>\n"]
    for u in users_by_username.values():
        status = "активен" if u['is_active'] else "неактивен"
        lines.append(f"• @{u['telegram_username']} — {u['full_name']} ({u['role']}, {status})")
    return "\n".join(lines)

def handle_add_user(telegram_user_id, telegram_username, full_name, role, users_by_id, users_by_username):
    if not telegram_username or not telegram_user_id:
        return "Ошибка: не указан username или ID."
    username_lower = telegram_username.lower()
    if username_lower in users_by_username:
        return f"Пользователь @{telegram_username} уже существует."

    new_id = max([u['user_id'] for u in users_by_id.values()], default=0) + 1
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    new_user = {
        'user_id': new_id,
        'telegram_user_id': int(telegram_user_id),
        'telegram_username': telegram_username,
        'full_name': full_name or telegram_username,
        'registration_timestamp': now,
        'last_login': now,
        'is_active': True,
        'role': role
    }
    users_by_id[new_user['telegram_user_id']] = new_user
    users_by_username[username_lower] = new_user
    save_users(users_by_id)
    return f"Пользователь @{telegram_username} успешно добавлен как «{role}»."

def handle_remove_user(target_username, users_by_id, users_by_username):
    username_lower = target_username.lower()
    if username_lower not in users_by_username:
        return f"Пользователь @{target_username} не найден."
    user = users_by_username[username_lower]
    del users_by_username[username_lower]
    del users_by_id[user['telegram_user_id']]
    save_users(users_by_id)
    return f"Пользователь @{target_username} удалён."

def handle_list_invites():
    from .invite_manager import get_all_invites
    invites = get_all_invites()
    if not invites:
        return "Нет активных приглашений."
    lines = ["<b>Активные приглашения:</b>\n"]
    for inv in invites:
        if inv['is_active'] == 'True' and not inv['used_by']:
            link = f"https://t.me/K2NeuroAssist_bot?start=invite_{inv['code']}"
            lines.append(f"• <a href='{link}'>invite_{inv['code'][:8]}...</a> (создал: @{inv['created_by_admin_username']})")
    return "\n".join(lines) if len(lines) > 1 else "Нет активных приглашений."