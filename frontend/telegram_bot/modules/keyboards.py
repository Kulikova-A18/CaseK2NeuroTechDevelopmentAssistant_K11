"""
Keyboard generators for Telegram bot.
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Keyboards:
    """Class for creating keyboards."""
    
    # ============================================================================
    # MAIN MENUS (Reply Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """
        Get main menu keyboard.
        
        @return: Main menu ReplyKeyboardMarkup
        """
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Задачи"), KeyboardButton(text="Создать задачу")],
                [KeyboardButton(text="AI Анализ"), KeyboardButton(text="Экспорт")],
                [KeyboardButton(text="Профиль"), KeyboardButton(text="Помощь")]
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите действие..."
        )
    
    @staticmethod
    def get_tasks_menu() -> ReplyKeyboardMarkup:
        """
        Get tasks menu keyboard.
        
        @return: Tasks menu ReplyKeyboardMarkup
        """
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Мои задачи"), KeyboardButton(text="Все задачи")],
                [KeyboardButton(text="Поиск по фильтрам"), KeyboardButton(text="Изменить статус")],
                [KeyboardButton(text="Назад в меню")]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def get_cancel_keyboard() -> ReplyKeyboardMarkup:
        """
        Get cancel action keyboard.
        
        @return: Cancel keyboard ReplyKeyboardMarkup
        """
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
    
    # ============================================================================
    # TASK-RELATED KEYBOARDS (Inline Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_task_status_keyboard(task_id: int) -> InlineKeyboardMarkup:
        """
        Get task status selection inline keyboard.
        
        @param task_id: Task ID for callback data
        @return: Status selection keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        statuses = [
            ("К выполнению", "todo"),
            ("В процессе", "in_progress"),
            ("На проверке", "in_review"),
            ("Завершено", "done"),
            ("Отложено", "paused"),
            ("Отменено", "cancelled")
        ]
        
        for display_name, status_value in statuses:
            builder.button(
                text=display_name,
                callback_data=f"change_status:{task_id}:{status_value}"
            )
        
        builder.button(
            text="Назад к задаче",
            callback_data=f"task_detail:{task_id}"
        )
        
        builder.button(
            text="Отмена",
            callback_data=f"cancel_status_change:{task_id}"
        )
        
        builder.adjust(2)
        return builder.as_markup()
    
    @staticmethod
    def get_task_filters_keyboard() -> InlineKeyboardMarkup:
        """
        Get task filters inline keyboard.
        
        @return: Filters InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        # Status filters
        builder.button(text="To Do", callback_data="filter_status:todo")
        builder.button(text="In Progress", callback_data="filter_status:in_progress")
        builder.button(text="Done", callback_data="filter_status:done")
        
        # Priority filters
        builder.button(text="Низкий", callback_data="filter_priority:low")
        builder.button(text="Средний", callback_data="filter_priority:medium")
        builder.button(text="Высокий", callback_data="filter_priority:high")
        builder.button(text="Срочный", callback_data="filter_priority:urgent")
        
        # Assignee filters
        builder.button(text="Мои задачи", callback_data="filter_assignee:me")
        
        # Date filters
        builder.button(text="Сегодня", callback_data="filter_today:true")
        builder.button(text="Неделя", callback_data="filter_week:true")
        
        # Action buttons
        builder.button(text="Очистить", callback_data="filter_clear:all")
        builder.button(text="Применить", callback_data="filter_apply:true")
        
        builder.adjust(3, 4, 1, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_priority_selection_keyboard(task_id: int = None) -> InlineKeyboardMarkup:
        """
        Get priority selection inline keyboard.
        
        @param task_id: Task ID for callback data (optional)
        @return: Priority keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        if task_id:
            builder.button(text="Низкий", callback_data=f"priority_{task_id}:low")
            builder.button(text="Средний", callback_data=f"priority_{task_id}:medium")
            builder.button(text="Высокий", callback_data=f"priority_{task_id}:high")
            builder.button(text="Срочный", callback_data=f"priority_{task_id}:urgent")
        else:
            builder.button(text="Низкий", callback_data="priority:low")
            builder.button(text="Средний", callback_data="priority:medium")
            builder.button(text="Высокий", callback_data="priority:high")
            builder.button(text="Срочный", callback_data="priority:urgent")
        
        builder.adjust(2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
        """
        Get task actions inline keyboard.
        
        @param task_id: Task ID for callback data
        @return: Task actions keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        # Status actions
        builder.button(text="Изменить статус", callback_data=f"task_change_status:{task_id}")
        
        # Editing actions
        builder.button(text="Редактировать", callback_data=f"edit_task:{task_id}")
        builder.button(text="Изменить дедлайн", callback_data=f"change_due:{task_id}")
        builder.button(text="Переназначить", callback_data=f"reassign:{task_id}")
        
        # Delete action
        builder.button(text="Удалить", callback_data=f"delete_task:{task_id}")
        
        # Navigation
        builder.button(text="Назад к списку", callback_data="back_to_tasks_list")
        
        builder.adjust(1, 2, 2, 1, 1)
        return builder.as_markup()
    
    @staticmethod
    def get_task_list_navigation(total_pages: int, current_page: int, filters: dict = None) -> InlineKeyboardMarkup:
        """
        Get task list navigation inline keyboard.
        
        @param total_pages: Total number of pages
        @param current_page: Current page number
        @param filters: Current filters (for preserving state)
        @return: Navigation keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        # Page navigation
        if current_page > 1:
            builder.button(text="◀️ Назад", callback_data=f"page_{current_page-1}")
        
        builder.button(text=f"{current_page}/{total_pages}", callback_data="current_page")
        
        if current_page < total_pages:
            builder.button(text="Вперед ▶️", callback_data=f"page_{current_page+1}")
        
        # Filter actions
        builder.button(text="Фильтры", callback_data="show_filters")
        builder.button(text="Создать задачу", callback_data="create_new_task")
        
        builder.adjust(3, 2)
        return builder.as_markup()
    
    # ============================================================================
    # ANALYSIS KEYBOARDS (Inline Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_analysis_period_keyboard() -> InlineKeyboardMarkup:
        """
        Get analysis period selection inline keyboard.
        
        @return: Analysis period keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Неделя", callback_data="analysis_period:last_week"),
            InlineKeyboardButton(text="Месяц", callback_data="analysis_period:last_month"),
            InlineKeyboardButton(text="Квартал", callback_data="analysis_period:last_quarter"),
            InlineKeyboardButton(text="Все время", callback_data="analysis_period:all_time"),
        )
        
        builder.adjust(2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_analysis_type_keyboard() -> InlineKeyboardMarkup:
        """
        Get analysis type selection inline keyboard.
        
        @return: Analysis type keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Общий отчет", callback_data="analysis_type:overview"),
            InlineKeyboardButton(text="По пользователям", callback_data="analysis_type:by_user"),
            InlineKeyboardButton(text="По статусам", callback_data="analysis_type:by_status"),
            InlineKeyboardButton(text="По приоритетам", callback_data="analysis_type:by_priority"),
        )
        
        builder.adjust(2, 2)
        return builder.as_markup()
    
    # ============================================================================
    # EXPORT KEYBOARDS (Inline Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_export_format_keyboard() -> InlineKeyboardMarkup:
        """
        Get export format selection inline keyboard.
        
        @return: Export format keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="CSV", callback_data="export_format:csv"),
            InlineKeyboardButton(text="Excel", callback_data="export_format:excel")
        )
        
        builder.adjust(3)
        return builder.as_markup()
    
    @staticmethod
    def get_export_scope_keyboard() -> InlineKeyboardMarkup:
        """
        Get export scope selection inline keyboard.
        
        @return: Export scope keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Мои задачи", callback_data="export_scope:my_tasks"),
            InlineKeyboardButton(text="Все задачи", callback_data="export_scope:all_tasks"),
            InlineKeyboardButton(text="По фильтрам", callback_data="export_scope:filtered"),
        )
        
        builder.adjust(2, 1)
        return builder.as_markup()
    
    # ============================================================================
    # USER & PROFILE KEYBOARDS (Inline Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_profile_actions_keyboard() -> InlineKeyboardMarkup:
        """
        Get profile actions inline keyboard.
        
        @return: Profile actions keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Обновить профиль", callback_data="profile:refresh"),
            InlineKeyboardButton(text="Изменить настройки", callback_data="profile:settings"),
            InlineKeyboardButton(text="Выйти", callback_data="profile:logout"),
            InlineKeyboardButton(text="Помощь", callback_data="profile:help"),
        )
        
        builder.adjust(2, 1, 1)
        return builder.as_markup()
    
    # ============================================================================
    # NAVIGATION KEYBOARDS (Inline Keyboards)
    # ============================================================================
    
    @staticmethod
    def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
        """
        Get back to menu inline keyboard.
        
        @return: Back to menu keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Главное меню", callback_data="navigation:main_menu"),
            InlineKeyboardButton(text="Назад", callback_data="navigation:back"),
        )
        
        builder.adjust(2)
        return builder.as_markup()
    
    @staticmethod
    def get_confirmation_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
        """
        Get confirmation inline keyboard.
        
        @param action: Action to confirm (delete, update, etc.)
        @param item_id: Item ID (optional)
        @return: Confirmation keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        if item_id:
            builder.button(text="Да, подтверждаю", callback_data=f"confirm_{action}:{item_id}")
            builder.button(text="Нет, отмена", callback_data=f"cancel_{action}:{item_id}")
        else:
            builder.button(text="Да, подтверждаю", callback_data=f"confirm:{action}")
            builder.button(text="Нет, отмена", callback_data=f"cancel:{action}")
        
        builder.adjust(2)
        return builder.as_markup()
