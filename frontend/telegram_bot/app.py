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
from modules.handlers import *
from modules.callback_handlers import *
from modules.states import TaskStates, AnalysisStates
from aiogram.filters import Command, CommandStart
from aiogram import F

from datetime import datetime
import sys
from pathlib import Path

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
dp.message.register(process_task_title, TaskStates.waiting_for_title)
dp.message.register(process_task_title, TaskStates.waiting_for_title)
dp.message.register(process_task_description, TaskStates.waiting_for_description)

dp.message.register(cmd_change_task_status, F.text == "Изменить статус")
dp.callback_query.register(handle_status_change_callback, F.data.startswith("change_status:"))
dp.callback_query.register(handle_cancel_status_change_callback, F.data.startswith("cancel_status_change:"))
dp.message.register(process_task_id_for_status, TaskStates.waiting_for_task_id)

dp.callback_query.register(handle_change_status_menu_callback, F.data.startswith("change_status_menu:"))

# И обработчик команды:
dp.message.register(cmd_change_task_status, Command("changestatus"))
dp.message.register(cmd_change_task_status, F.text == "Изменить статус задачи")

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


class BotCronManager:
    """
    Manager for integrating cron functionality with the bot.
    Handles initialization, startup, and shutdown of cron tasks.
    """
    
    def __init__(self):
        """Initialize the cron manager."""
        self.greeting_cron = None
        self.config_path = "config.yaml"
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize cron system for the bot.
        
        :return: True if initialization successful, False otherwise
        """
        try:
            # Import cron_modules
            from cron_modules import setup_cron_for_bot
            
            logger.info("Initializing cron system for bot...")
            
            # Setup cron for bot using the module function
            self.greeting_cron = await setup_cron_for_bot(
                bot=bot,
                user_sessions=user_sessions,
                config_path=self.config_path
            )
            
            if not self.greeting_cron:
                logger.warning("Failed to create cron manager instance")
                return False
            
            # Check if cron is enabled
            if not self.greeting_cron.is_cron_enabled():
                logger.info("Cron is disabled or not available in configuration")
                self._initialized = True
                return True
            
            # Get configuration info for logging
            if hasattr(self.greeting_cron, 'get_telegram_cron_config'):
                cron_config = self.greeting_cron.get_telegram_cron_config()
                if cron_config:
                    logger.info(f"Telegram cron config loaded: enabled={cron_config.get('enabled')}")
            
            self._initialized = True
            logger.info("Cron system initialized successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"Cron modules not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing cron system: {e}")
            return False
    
    def get_status(self) -> dict:
        """
        Get cron system status.
        
        :return: Dictionary with cron status information
        """
        if not self._initialized or not self.greeting_cron:
            return {"status": "not_initialized"}
        
        try:
            return self.greeting_cron.get_status()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def manual_send_greetings(self) -> dict:
        """
        Manual send greetings for testing.
        
        :return: Dictionary with sending results
        """
        if not self._initialized or not self.greeting_cron:
            return {"error": "Cron system not initialized"}
        
        try:
            return await self.greeting_cron.manual_send_greetings()
        except Exception as e:
            logger.error(f"Error in manual greetings send: {e}")
            return {"error": str(e)}
    
    async def run_greetings_now(self) -> dict:
        """
        Run greetings task immediately.
        
        :return: Dictionary with execution results
        """
        if not self._initialized or not self.greeting_cron:
            return {"error": "Cron system not initialized"}
        
        try:
            result = self.greeting_cron.run_greetings_job_now()
            if result is None:
                return {"error": "Failed to run greetings task"}
            return result
        except Exception as e:
            logger.error(f"Error running greetings task: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """
        Shutdown cron system gracefully.
        """
        if not self._initialized or not self.greeting_cron:
            return
        
        try:
            logger.info("Shutting down cron system...")
            
            # Stop all cron jobs
            success = self.greeting_cron.stop_all_cron_jobs()
            
            if success:
                logger.info("Cron system stopped successfully")
            else:
                logger.warning("Failed to stop cron system gracefully")
                
        except Exception as e:
            logger.error(f"Error during cron shutdown: {e}")


# Global instance of cron manager
cron_manager = BotCronManager()


async def setup_bot_commands():
    """Setup bot commands with cron-related commands if available."""
    try:
        from aiogram.types import BotCommand, BotCommandScopeDefault
        
        # Base commands
        commands = [
            BotCommand(command=cmd, description=desc)
            for cmd, desc in BotConstants.COMMANDS
        ]
        
        # Add cron-related commands if cron is available
        if cron_manager._initialized and cron_manager.greeting_cron:
            cron_commands = [
                BotCommand(command="/cron_status", description="Check cron system status"),
                BotCommand(command="/send_greetings", description="Send greetings manually"),
            ]
            commands.extend(cron_commands)
            logger.info("Added cron-related bot commands")
        
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info(f"Bot commands set: {len(commands)} commands total")
        
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")


# Command handlers for cron functionality
async def cmd_cron_status(message, state):
    """
    Handler for /cron_status command.
    Shows cron system status.
    """
    try:
        status = cron_manager.get_status()
        
        # Format status message
        status_text = "*Cron System Status*\n\n"
        
        if status.get("status") == "not_initialized":
            status_text += "Cron system not initialized\n"
        elif status.get("status") == "error":
            status_text += f"Error: {status.get('error', 'Unknown')}\n"
        else:
            # Show basic status
            cron_enabled = status.get("cron_enabled", False)
            initialized = status.get("initialized", False)
            
            status_text += f"• Cron enabled: {'done' if cron_enabled else 'fail'}\n"
            status_text += f"• System initialized: {'done' if initialized else 'fail'}\n"
            
            # Show job information if available
            if "job_count" in status:
                status_text += f"\n*Jobs Information*\n"
                status_text += f"• Total jobs: {status.get('job_count', 0)}\n"
                
                # Show telegram-specific jobs
                telegram_jobs = []
                for job_key in ["telegram_sync_job", "telegram_greetings_job"]:
                    job_info = status.get(job_key)
                    if job_info:
                        telegram_jobs.append(job_info)
                
                if telegram_jobs:
                    status_text += f"\n🤖 *Telegram Jobs*\n"
                    for job in telegram_jobs:
                        name = job.get('name', 'Unknown')
                        enabled = job.get('enabled', False)
                        next_run = job.get('next_run', 'Not scheduled')
                        status_text += f"• {name}: {'done' if enabled else 'fail'} (next: {next_run})\n"
        
        await message.answer(status_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in cron_status command: {e}")
        await message.answer(f"Error getting cron status: {str(e)[:100]}")


async def cmd_send_greetings(message, state):
    """
    Handler for /send_greetings command.
    Manually sends greetings to all users.
    """
    try:
        await message.answer("⏳ Sending greetings to all users...")
        
        result = await cron_manager.manual_send_greetings()
        
        if "error" in result:
            await message.answer(f"Error: {result['error'][:200]}")
        else:
            success = result.get('success', 0)
            failed = result.get('failed', 0)
            total = result.get('users_total', 0)
            
            response = f"done Greetings sent successfully!\n\n"
            response += f"• Total users: {total}\n"
            response += f"• Successful: {success}\n"
            response += f"• Failed: {failed}\n"
            
            if success > 0:
                response += f"\n📨 Last execution: {result.get('timestamp', 'N/A')}"
            
            await message.answer(response)
            
    except Exception as e:
        logger.error(f"Error in send_greetings command: {e}")
        await message.answer(f"Error sending greetings: {str(e)[:100]}")


# Register cron command handlers
dp.message.register(cmd_cron_status, Command("cron_status"))
dp.message.register(cmd_send_greetings, Command("send_greetings"))


async def test_greetings_on_startup():
    """
    Test greetings sending on bot startup (optional).
    Can be enabled/disabled in config.
    """
    try:
        if not cron_manager._initialized:
            return
        
        # Get config to check if we should send on startup
        if hasattr(cron_manager.greeting_cron, 'get_telegram_cron_config'):
            config = cron_manager.greeting_cron.get_telegram_cron_config()
            send_on_startup = config.get('send_on_startup', False)
            
            if send_on_startup:
                logger.info("Sending test greetings on startup...")
                result = await cron_manager.run_greetings_now()
                logger.info(f"Test greetings result: {result}")
            else:
                logger.info("Skipping greetings on startup (disabled in config)")
                
    except Exception as e:
        logger.error(f"Error in test greetings on startup: {e}")


async def main():
    """Main bot startup function."""
    logger.info("Starting Telegram bot...")
    
    # Initialize cron system
    cron_initialized = await cron_manager.initialize()
    
    if cron_initialized:
        logger.info("Cron system initialized successfully")
        
        # Get and log cron status
        status = cron_manager.get_status()
        logger.info(f"Cron status: {status.get('status', 'unknown')}")
        
        # Test greetings on startup if configured
        await test_greetings_on_startup()
    else:
        logger.warning("Cron system not initialized or disabled")
    
    # Setup bot commands (including cron commands if available)
    await setup_bot_commands()
    
    logger.info(f"API server: {BotConstants.API_BASE_URL}")
    logger.info(f"Bot token configured: {'Yes' if BotConstants.BOT_TOKEN else 'No'}")
    
    try:
        # Start bot polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user request")
    except Exception as e:
        logger.error(f"Error in bot main loop: {e}")
    finally:
        # Graceful shutdown
        logger.info("Shutting down bot...")
        
        # Shutdown cron system
        await cron_manager.shutdown()
        
        # Close bot session
        await bot.session.close()
        logger.info("Bot shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())