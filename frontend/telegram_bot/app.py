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

import asyncio
from datetime import datetime

async def greeting_timer_to_all_users():
    """Таймер для отправки приветствия всем пользователям бота"""
    logger.info("Запуск таймера рассылки приветствий...")
    
    # Счетчик для отслеживания количества отправок
    iteration = 0
    
    while True:
        iteration += 1
        try:
            # Получаем всех пользователей из сессий
            all_users = user_sessions.get_all_users()
            
            if not all_users:
                logger.info(f"Итерация {iteration}: Нет активных пользователей")
            else:
                logger.info(f"Итерация {iteration}: Найдено {len(all_users)} пользователей")
                
                success_count = 0
                fail_count = 0
                
                for user_id in all_users:
                    try:
                        # Получаем информацию о пользователе
                        user_info = user_sessions.get_session(user_id)
                        username = user_info.get('username', '')
                        first_name = user_info.get('first_name', '')
                        
                        # Формируем персонализированное сообщение
                        name_to_use = first_name or username or "Пользователь"
                        
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"👋 Привет, {name_to_use}!\n"
                                 f"🕒 Время: {datetime.now().strftime('%H:%M:%S')}\n"
                                 f"🤖 Бот активен и работает!"
                        )
                        success_count += 1
                        logger.debug(f"Сообщение отправлено пользователю {user_id} (@{username})")
                        
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"Ошибка отправки пользователю {user_id}: {str(e)[:100]}")
                        continue
                    
                    # Пауза между отправками (чтобы не превысить лимиты Telegram)
                    await asyncio.sleep(0.3)
                
                logger.info(f"Итерация {iteration}: Успешно {success_count}, Ошибок {fail_count}")
            
            # Ждем 5 секунд перед следующей рассылкой
            logger.debug(f"Итерация {iteration}: Ожидание 5 секунд...")
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Критическая ошибка в таймере (итерация {iteration}): {e}")
            await asyncio.sleep(5)  # Ждем перед повторной попыткой

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
    
    # Запуск таймера рассылки приветствий
    timer_task = asyncio.create_task(greeting_timer_to_all_users())
    logger.info("Таймер рассылки приветствий запущен (каждые 5 секунд)")
    
    try:
        # Start bot polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен по запросу пользователя")
    finally:
        # Остановка таймера при завершении
        timer_task.cancel()
        logger.info("Таймер рассылки остановлен")


if __name__ == '__main__':
    asyncio.run(main())