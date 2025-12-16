"""
FSM states for Telegram bot.
"""

from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    """States for creating/editing tasks."""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()
    waiting_for_due_date = State()
    waiting_for_tags = State()
    waiting_for_task_id = State()
    waiting_for_update_field = State()
    waiting_for_update_value = State()


class UserStates(StatesGroup):
    """States for user management."""
    waiting_for_username = State()
    waiting_for_full_name = State()
    waiting_for_role = State()


class AnalysisStates(StatesGroup):
    """States for AI analysis."""
    waiting_for_period = State()