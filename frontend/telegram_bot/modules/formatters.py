"""
Message formatting utilities.
"""

import json
from typing import Dict, Any, List
from modules.constants import BotConstants


class MessageFormatter:
    """Class for formatting messages."""
    
    @staticmethod
    def format_task(task: Dict[str, Any]) -> str:
        """
        Format single task for display.
        
        @param task: Task data dictionary
        @return: Formatted task string
        """
        status_display = BotConstants.STATUS_DISPLAY.get(task.get('status', 'todo'), 'To Do')
        priority_display = BotConstants.PRIORITY_DISPLAY.get(task.get('priority', 'medium'), 'Средний')
        
        lines = [
            f"Задача #{task.get('task_id', 'N/A')}",
            f"",
            f"Заголовок: {task.get('title', 'Без названия')}",
            f"",
        ]
        
        if task.get('description'):
            desc = task['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"Описание:\n{desc}")
        
        lines.extend([
            f"",
            f"Назначена: {task.get('assignee_name', task.get('assignee', 'Не назначена'))}",
            f"Создатель: {task.get('creator_name', task.get('creator', 'Неизвестно'))}",
            f"",
            f"Статус: {status_display}",
            f"Приоритет: {priority_display}",
        ])
        
        if task.get('created_at'):
            created_date = task['created_at'].split('T')[0] if 'T' in task['created_at'] else task['created_at'][:10]
            lines.append(f"Создана: {created_date}")
        
        if task.get('due_date'):
            due_date = task['due_date']
            days_remaining = task.get('days_remaining')
            if days_remaining is not None:
                if days_remaining < 0:
                    lines.append(f"Дедлайн: Просрочено на {abs(days_remaining)} дней")
                elif days_remaining == 0:
                    lines.append(f"Дедлайн: Сегодня")
                elif days_remaining <= 2:
                    lines.append(f"Дедлайн: {due_date} (осталось {days_remaining} дней)")
                else:
                    lines.append(f"Дедлайн: {due_date} (осталось {days_remaining} дней)")
            else:
                lines.append(f"Дедлайн: {due_date}")
        
        if task.get('tags'):
            tags = task['tags']
            if isinstance(tags, list):
                lines.append(f"Теги: {' '.join([f'#{tag}' for tag in tags])}")
            elif isinstance(tags, str):
                try:
                    tags_list = json.loads(tags)
                    lines.append(f"Теги: {' '.join([f'#{tag}' for tag in tags_list])}")
                except:
                    lines.append(f"Теги: {tags}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_tasks_list(tasks: List[Dict[str, Any]], total_count: int = None) -> str:
        """
        Format list of tasks for display.
        
        @param tasks: List of task dictionaries
        @param total_count: Total number of tasks (if known)
        @return: Formatted tasks list string
        """
        if not tasks:
            return "Задачи не найдены"
        
        max_tasks = BotConstants.MAX_TASKS_TO_SHOW
        displayed_tasks = tasks[:max_tasks]
        
        if total_count is None:
            total_count = len(tasks)
        
        lines = [f"Найдено задач: {total_count}", ""]
        
        if total_count > max_tasks:
            lines.append(f"Показаны первые {max_tasks} задач")
            lines.append(f"Для просмотра всех задач используйте экспорт")
            lines.append("")
        
        for task in displayed_tasks:
            status_display = BotConstants.STATUS_DISPLAY.get(task.get('status', 'todo'), 'To Do')[:1]
            priority_display = BotConstants.PRIORITY_DISPLAY.get(task.get('priority', 'medium'), 'Средний')[:1]
            
            task_id = task.get('task_id', '?')
            title = task.get('title', 'Без названия')[:30]
            assignee = task.get('assignee_name', task.get('assignee', 'Не назначена'))[:15]
            
            line = f"#{task_id} - {title} • {assignee} ({status_display}/{priority_display})"
            
            if task.get('due_date'):
                days_remaining = task.get('days_remaining', 0)
                if days_remaining < 0:
                    line += f" [Просрочено]"
                elif days_remaining == 0:
                    line += f" [Сегодня]"
                elif days_remaining <= 2:
                    line += f" [Скоро]"
            
            lines.append(line)
        
        if total_count > max_tasks:
            lines.append(f"\n... и еще {total_count - max_tasks} задач")
            lines.append("Для просмотра всех задач используйте экспорт")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_user_info(user_info: Dict[str, Any]) -> str:
        """
        Format user information for display.
        
        @param user_info: User information dictionary
        @return: Formatted user info string
        """
        if not user_info:
            return "Информация о пользователе недоступна"
        
        # Extract user data
        user = {}
        if 'user' in user_info:
            user = user_info['user']
        elif 'data' in user_info and 'user' in user_info['data']:
            user = user_info['data']['user']
        
        permissions = user_info.get('permissions', {})
        
        lines = [
            f"Ваш профиль",
            f"",
            f"Имя: {user.get('full_name', 'Не указано')}",
            f"Telegram: {user.get('telegram_username', 'Не указан')}",
            f"Роль: {user.get('role', 'member').title()}",
            f"Статус: {'Активен' if str(user.get('is_active', '')).lower() == 'true' else 'Неактивен'}",
            f"",
        ]
        
        if user.get('email'):
            lines.append(f"Email: {user['email']}")
        if user.get('department'):
            lines.append(f"Отдел: {user['department']}")
        
        lines.extend([
            f"",
            f"Права доступа:",
        ])
        
        if permissions.get('can_create_tasks'):
            lines.append(f"- Создавать задачи")
        if permissions.get('can_edit_tasks'):
            lines.append(f"- Редактировать задачи")
        if permissions.get('can_delete_tasks'):
            lines.append(f"- Удалять задачи")
        if permissions.get('can_export'):
            lines.append(f"- Экспортировать данные")
        if permissions.get('can_use_llm'):
            lines.append(f"- Использовать AI анализ")
        if permissions.get('can_manage_users'):
            lines.append(f"- Управлять пользователями")
        
        llm_limit = permissions.get('llm_daily_limit', 0)
        lines.append(f"\nЛимит AI запросов: {llm_limit}/день")
        
        if user.get('last_login'):
            lines.append(f"")
            lines.append(f"Последний вход: {user['last_login']}")
        
        return "\n".join(lines)