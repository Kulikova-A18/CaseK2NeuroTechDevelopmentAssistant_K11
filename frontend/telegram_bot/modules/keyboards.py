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
                [KeyboardButton(text="Поиск по фильтрам")],
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
    
    @staticmethod
    def get_task_filters_keyboard() -> InlineKeyboardMarkup:
        """
        Get task filters inline keyboard.
        
        @return: Filters InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="To Do", callback_data="filter_status:todo"),
            InlineKeyboardButton(text="In Progress", callback_data="filter_status:in_progress"),
            InlineKeyboardButton(text="Done", callback_data="filter_status:done"),
            InlineKeyboardButton(text="Низкий", callback_data="filter_priority:low"),
            InlineKeyboardButton(text="Средний", callback_data="filter_priority:medium"),
            InlineKeyboardButton(text="Высокий", callback_data="filter_priority:high"),
            InlineKeyboardButton(text="Срочный", callback_data="filter_priority:urgent"),
            InlineKeyboardButton(text="Мои задачи", callback_data="filter_assignee:me"),
            InlineKeyboardButton(text="Сегодня", callback_data="filter_today:true"),
            InlineKeyboardButton(text="Очистить", callback_data="filter_clear:all"),
            InlineKeyboardButton(text="Применить", callback_data="filter_apply:true"),
        )
        
        builder.adjust(3, 3, 2, 1, 1)
        return builder.as_markup()
    
    @staticmethod
    def get_priority_keyboard() -> InlineKeyboardMarkup:
        """
        Get priority selection inline keyboard.
        
        @return: Priority keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Низкий", callback_data="priority:low"),
            InlineKeyboardButton(text="Средний", callback_data="priority:medium"),
            InlineKeyboardButton(text="Высокий", callback_data="priority:high"),
            InlineKeyboardButton(text="Срочный", callback_data="priority:urgent"),
        )
        
        builder.adjust(2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_status_keyboard(task_id: int = None) -> InlineKeyboardMarkup:
        """
        Get status change inline keyboard.
        
        @param task_id: Task ID for callback data
        @return: Status keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        if task_id:
            builder.add(
                InlineKeyboardButton(text="To Do", callback_data=f"status_{task_id}:todo"),
                InlineKeyboardButton(text="In Progress", callback_data=f"status_{task_id}:in_progress"),
                InlineKeyboardButton(text="Done", callback_data=f"status_{task_id}:done"),
            )
        else:
            builder.add(
                InlineKeyboardButton(text="To Do", callback_data="status:todo"),
                InlineKeyboardButton(text="In Progress", callback_data="status:in_progress"),
                InlineKeyboardButton(text="Done", callback_data="status:done"),
            )
        
        builder.adjust(3)
        return builder.as_markup()
    
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
        )
        
        builder.adjust(3)
        return builder.as_markup()
    
    @staticmethod
    def get_export_format_keyboard() -> InlineKeyboardMarkup:
        """
        Get export format selection inline keyboard.
        
        @return: Export format keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="CSV", callback_data="export_format:csv"),
            InlineKeyboardButton(text="Excel", callback_data="export_format:excel"),
        )
        
        builder.adjust(2)
        return builder.as_markup()
    
    @staticmethod
    def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
        """
        Get task actions inline keyboard.
        
        @param task_id: Task ID for callback data
        @return: Task actions keyboard InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        builder.add(
            InlineKeyboardButton(text="Редактировать", callback_data=f"edit_task:{task_id}"),
            InlineKeyboardButton(text="Изменить статус", callback_data=f"change_status:{task_id}"),
            InlineKeyboardButton(text="Изменить дедлайн", callback_data=f"change_due:{task_id}"),
            InlineKeyboardButton(text="Переназначить", callback_data=f"reassign:{task_id}"),
            InlineKeyboardButton(text="Удалить", callback_data=f"delete_task:{task_id}"),
        )
        
        builder.adjust(2, 2, 1)
        return builder.as_markup()