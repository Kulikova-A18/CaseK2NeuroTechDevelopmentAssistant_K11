"""
Telegram bot for task management system.
Interacts with REST API server, provides interface for task management via Telegram.
"""

import os
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from modules import BotConstants, user_sessions
from modules.handlers import (
    cmd_start, cmd_login, cmd_tasks, cmd_my_tasks, cmd_all_tasks,
    cmd_filter_search, cmd_new_task, cmd_analyze, cmd_export,
    cmd_profile, cmd_back_to_menu, cmd_cancel, cmd_help_button,
    cmd_help, handle_unknown_message
)
from modules.callback_handlers import (
    handle_export_all_tasks, handle_export_format,
    handle_task_filters, handle_analysis_period
)
from aiogram.filters import Command, CommandStart
from aiogram import F

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BotConstants.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register message handlers
dp.message.register(cmd_start, CommandStart())
dp.message.register(cmd_login, Command("login"))
dp.message.register(cmd_tasks, F.text == "Задачи")
dp.message.register(cmd_tasks, Command("tasks"))
dp.message.register(cmd_my_tasks, F.text == "Мои задачи")
dp.message.register(cmd_all_tasks, F.text == "Все задачи")
dp.message.register(cmd_filter_search, F.text == "Поиск по фильтрам")
dp.message.register(cmd_new_task, F.text == "Создать задачу")
dp.message.register(cmd_new_task, Command("newtask"))
dp.message.register(cmd_analyze, F.text == "AI Анализ")
dp.message.register(cmd_analyze, Command("analyze"))
dp.message.register(cmd_export, F.text == "Экспорт")
dp.message.register(cmd_export, Command("export"))
dp.message.register(cmd_profile, F.text == "Профиль")
dp.message.register(cmd_profile, Command("profile"))
dp.message.register(cmd_back_to_menu, F.text == "Назад в меню")
dp.message.register(cmd_cancel, F.text == "Отмена")
dp.message.register(cmd_help_button, F.text == "Помощь")
dp.message.register(cmd_help, Command("help"))
dp.message.register(handle_unknown_message)

# Register callback handlers
dp.callback_query.register(handle_export_all_tasks, F.data == "export_all_tasks")
dp.callback_query.register(handle_export_format, F.data.startswith("export_format:"))
dp.callback_query.register(handle_task_filters, F.data.startswith("filter_"))
dp.callback_query.register(handle_analysis_period, F.data.startswith("analysis_period:"))


async def main():
    """Main bot startup function."""
    logger.info("Starting Telegram bot...")
    
    # Set bot commands
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command=cmd, description=desc)
        for cmd, desc in BotConstants.COMMANDS
    ]
    await bot.set_my_commands(commands)
    
    logger.info(f"Bot started with {len(commands)} commands")
    logger.info(f"API server: {BotConstants.API_BASE_URL}")
    
    # Start bot
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())