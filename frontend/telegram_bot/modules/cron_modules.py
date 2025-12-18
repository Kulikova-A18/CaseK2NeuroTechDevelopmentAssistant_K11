"""
Module for working with cron tasks in Telegram bot.
Integration with cron scheduler for periodic tasks.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TelegramGreetingCron:
    """
    Class for managing cron greeting tasks.
    Integrates cron system with Telegram bot.
    """
    
    def __init__(self, bot, user_sessions_module):
        """
        Initialize cron greetings manager.
        
        :param bot: aiogram Bot instance
        :param user_sessions_module: User sessions module
        """
        self.bot = bot
        self.user_sessions = user_sessions_module
        self.cron_manager = None
        self._initialized = False
        self._cron_module_available = False
        
        # Check cron module availability
        self._check_cron_availability()
    
    def _check_cron_availability(self) -> bool:
        """
        Check cron module availability.
        
        :return: True if cron module is available, False otherwise
        """
        try:
            # Add parent directory to path
            current_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(current_dir))
            
            # Try to import cron module
            from cron import get_cron_manager
            self._cron_module_available = True
            logger.info("Cron module available")
            return True
            
        except ImportError as e:
            logger.warning(f"Cron module not available: {e}")
            self._cron_module_available = False
            return False
        except Exception as e:
            logger.warning(f"Error checking cron module: {e}")
            self._cron_module_available = False
            return False
    
    def init_cron(self, config_path: Optional[str] = None) -> bool:
        """
        Initialize cron system.
        
        :param config_path: Path to configuration file
        :return: True if initialization successful, False otherwise
        """
        if not self._cron_module_available:
            logger.error("Cron module not available. Ensure cron.py file exists")
            return False
        
        try:
            # Import cron manager
            from cron import get_cron_manager
            
            # Get cron manager instance
            self.cron_manager = get_cron_manager(config_path)
            
            # Check if cron is globally enabled
            if not self.cron_manager.is_enabled():
                logger.warning("Cron disabled in configuration (cron.enabled: false)")
                return False
            
            # Override sync_telegram_status method for sending greetings
            # This allows using existing task from config
            original_method = self.cron_manager.sync_telegram_status
            
            def custom_telegram_sync():
                """Custom Telegram sync implementation for sending greetings."""
                try:
                    return asyncio.run(self._send_greetings_async())
                except RuntimeError:
                    # If event loop already running, create new one
                    return asyncio.new_event_loop().run_until_complete(self._send_greetings_async())
            
            # Replace the method
            self.cron_manager.sync_telegram_status = custom_telegram_sync
            
            # Also update method mapping for run_job_now
            if hasattr(self.cron_manager, 'job_methods'):
                self.cron_manager.job_methods['sync_telegram_status'] = custom_telegram_sync
                self.cron_manager.job_methods['send_telegram_greetings'] = custom_telegram_sync
            
            self._initialized = True
            logger.info("Cron system for greetings initialized successfully")
            
            # Check task configuration
            self._check_task_configuration()
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import cron module: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing cron: {e}")
            return False
    
    def _check_task_configuration(self):
        """Check task configuration in config.yaml."""
        try:
            if not self.cron_manager or not hasattr(self.cron_manager, 'config'):
                return
            
            jobs_config = self.cron_manager.config.get('cron', {}).get('jobs', {})
            
            # Check telegram_greetings task
            greetings_job = jobs_config.get('telegram_greetings')
            if greetings_job:
                enabled = greetings_job.get('enabled', False)
                schedule = greetings_job.get('schedule', 'not specified')
                task = greetings_job.get('task', 'not specified')
                
                logger.info(f"Found Telegram greetings task: enabled={enabled}, schedule='{schedule}', task='{task}'")
                
                if enabled and task == 'send_telegram_greetings':
                    logger.info("Telegram greetings task configured correctly")
                elif not enabled:
                    logger.warning("Telegram greetings task disabled in configuration")
                else:
                    logger.warning(f"Incorrect task configuration: task should be 'send_telegram_greetings', not '{task}'")
            else:
                logger.warning("Task 'telegram_greetings' not found in cron.jobs configuration")
            
            # Check telegram_sync task
            sync_job = jobs_config.get('telegram_sync')
            if sync_job:
                enabled = sync_job.get('enabled', False)
                schedule = sync_job.get('schedule', 'not specified')
                task = sync_job.get('task', 'not specified')
                
                logger.info(f"Found Telegram sync task: enabled={enabled}, schedule='{schedule}', task='{task}'")
                
                if enabled and task == 'sync_telegram_status':
                    logger.info("Telegram sync task configured correctly")
                elif not enabled:
                    logger.warning("Telegram sync task disabled in configuration")
                else:
                    logger.warning(f"Incorrect task configuration: task should be 'sync_telegram_status', not '{task}'")
            else:
                logger.warning("Task 'telegram_sync' not found in cron.jobs configuration")
                
        except Exception as e:
            logger.error(f"Error checking configuration: {e}")
    
    async def _send_greetings_async(self) -> Dict[str, Any]:
        """
        Async function for sending greetings to all users.
        
        :return: Dictionary with sending results
        """
        try:
            # Get all users
            all_users = self.user_sessions.get_all_users()
            
            if not all_users:
                logger.info("No active users for sending greetings")
                return {
                    "status": "skipped", 
                    "reason": "No active users", 
                    "timestamp": datetime.now().isoformat(),
                    "task": "send_telegram_greetings"
                }
            
            logger.info(f"Sending greetings to {len(all_users)} users...")
            
            success_count = 0
            fail_count = 0
            detailed_errors = []
            
            for user_id in all_users:
                try:
                    # Get user information
                    user_info = self.user_sessions.get_session(user_id)
                    if not user_info:
                        logger.warning(f"No information for user {user_id}")
                        continue
                    
                    username = user_info.get('username', '')
                    first_name = user_info.get('first_name', '')
                    
                    # Form personalized message
                    name_to_use = first_name or username or "User"
                    
                    # Send message
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"Hello, {name_to_use}!\n"
                             f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
                             f"Bot is active and working!"
                    )
                    success_count += 1
                    logger.debug(f"Message sent to user {user_id} (@{username})")
                    
                except Exception as e:
                    fail_count += 1
                    error_msg = f"User {user_id}: {str(e)[:100]}"
                    detailed_errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                
                # Pause between sends (to avoid Telegram API limits)
                await asyncio.sleep(0.3)
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "task": "send_telegram_greetings",
                "users_total": len(all_users),
                "success": success_count,
                "failed": fail_count,
                "status": "completed",
                "execution_time": datetime.now().isoformat()
            }
            
            if detailed_errors:
                result["errors"] = detailed_errors[:10]  # Limit errors in log
            
            logger.info(f"Greetings sent: successful {success_count}, errors {fail_count}")
            return result
            
        except Exception as e:
            logger.error(f"Critical error in greetings sending function: {e}")
            return {
                "error": str(e), 
                "timestamp": datetime.now().isoformat(),
                "task": "send_telegram_greetings",
                "status": "failed"
            }
    
    def start_greetings_cron(self) -> bool:
        """
        Start cron task for sending greetings.
        
        :return: True if task started successfully
        """
        if not self._initialized:
            logger.error("Cron system not initialized. Call init_cron() first")
            return False
        
        try:
            from cron import start_telegram_sync_cron_functionality
            
            # Start Telegram sync task
            success = start_telegram_sync_cron_functionality()
            
            if success:
                logger.info("Cron task for Telegram greetings started successfully")
                
                # Get task information
                if self.cron_manager:
                    job_info = self.cron_manager.get_specific_job_info('telegram_sync')
                    logger.info(f"Task information: {job_info}")
            else:
                logger.warning("Failed to start cron task for Telegram greetings")
                
                # Try alternative method
                if self.cron_manager:
                    logger.info("Trying alternative startup method...")
                    alt_success = self.cron_manager.start()
                    if alt_success:
                        logger.info("Cron manager started via alternative method")
            
            return success
            
        except ImportError as e:
            logger.error(f"Failed to import cron startup function: {e}")
            return False
        except Exception as e:
            logger.error(f"Error starting cron task: {e}")
            return False
    
    def start_all_cron_jobs(self) -> bool:
        """
        Start all cron tasks from configuration.
        
        :return: True if tasks started successfully
        """
        if not self._initialized:
            logger.error("Cron system not initialized. Call init_cron() first")
            return False
        
        try:
            from cron import start_cron_scheduler
            
            # Start all cron tasks
            success = start_cron_scheduler()
            
            if success:
                logger.info("All cron tasks started successfully")
                
                # Get information about all tasks
                if self.cron_manager:
                    jobs_info = self.cron_manager.get_job_info()
                    job_count = jobs_info.get('job_count', 0)
                    logger.info(f"Total tasks started: {job_count}")
                    
                    if job_count > 0:
                        for job in jobs_info.get('jobs', []):
                            logger.info(f"  - {job.get('name')}: next run {job.get('next_run')}")
            else:
                logger.warning("Failed to start cron tasks")
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting all cron tasks: {e}")
            return False
    
    def stop_greetings_cron(self) -> bool:
        """
        Stop greetings cron task.
        
        :return: True if stop successful
        """
        if not self._initialized or not self.cron_manager:
            logger.warning("Cron system not initialized or manager not available")
            return False
        
        try:
            # Try to stop specific task
            stop_methods = ['stop_specific_job', 'remove_job', 'pause_job']
            
            for method_name in stop_methods:
                if hasattr(self.cron_manager, method_name):
                    try:
                        method = getattr(self.cron_manager, method_name)
                        # Try with different job names
                        for job_name in ['telegram_sync', 'telegram_greetings']:
                            try:
                                success = method(job_name)
                                if success:
                                    logger.info(f"Greetings cron task stopped using {method_name}")
                                    return True
                            except:
                                continue
                    except:
                        continue
            
            # If specific stop failed, stop entire scheduler
            logger.warning("Failed to stop specific task, stopping entire scheduler")
            success = self.cron_manager.stop()
            return success
            
        except Exception as e:
            logger.error(f"Error stopping cron: {e}")
            return False
    
    def stop_all_cron_jobs(self) -> bool:
        """
        Stop all cron tasks.
        
        :return: True if stop successful
        """
        if not self._initialized or not self.cron_manager:
            return False
        
        try:
            success = self.cron_manager.stop()
            if success:
                logger.info("All cron tasks stopped")
            return success
        except Exception as e:
            logger.error(f"Error stopping all cron tasks: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get cron system status.
        
        :return: Dictionary with status
        """
        if not self._initialized or not self.cron_manager:
            return {
                "status": "not_initialized",
                "cron_module_available": self._cron_module_available,
                "initialized": self._initialized
            }
        
        try:
            status = self.cron_manager.get_job_info()
            status["cron_module_available"] = self._cron_module_available
            status["initialized"] = self._initialized
            
            # Add information about telegram tasks
            if hasattr(self.cron_manager, 'get_specific_job_info'):
                telegram_sync_info = self.cron_manager.get_specific_job_info('telegram_sync')
                telegram_greetings_info = self.cron_manager.get_specific_job_info('telegram_greetings')
                
                status["telegram_sync_job"] = telegram_sync_info
                status["telegram_greetings_job"] = telegram_greetings_info
            
            return status
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
                "cron_module_available": self._cron_module_available,
                "initialized": self._initialized
            }
    
    async def manual_send_greetings(self) -> Dict[str, Any]:
        """
        Manual greetings sending (for testing).
        
        :return: Sending results
        """
        logger.info("Manual greetings sending...")
        try:
            result = await self._send_greetings_async()
            logger.info(f"Manual sending result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in manual sending: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def run_greetings_job_now(self) -> Optional[Dict[str, Any]]:
        """
        Immediate execution of greetings task via cron manager.
        
        :return: Execution result or None on error
        """
        if not self._initialized or not self.cron_manager:
            logger.error("Cron system not initialized")
            return None
        
        try:
            # Try with different job names
            for job_name in ['telegram_sync', 'telegram_greetings']:
                try:
                    # Use run_job_now from cron manager
                    result = self.cron_manager.run_job_now(job_name)
                    logger.info(f"Task executed immediately: {result}")
                    return result
                except:
                    continue
            
            logger.error("Failed to execute greetings task with any job name")
            return None
        except Exception as e:
            logger.error(f"Error executing task immediately: {e}")
            return None
    
    def is_cron_enabled(self) -> bool:
        """
        Check if cron is enabled in the system.
        
        :return: True if cron is enabled and available
        """
        if not self._cron_module_available:
            return False
        
        try:
            from cron import is_cron_enabled as check_cron_enabled
            return check_cron_enabled()
        except:
            return False
    
    def get_telegram_cron_config(self) -> Dict[str, Any]:
        """
        Get Telegram cron configuration from config.yaml.
        
        :return: Dictionary with Telegram cron configuration
        """
        if not self._initialized or not self.cron_manager:
            return {}
        
        try:
            config = self.cron_manager.config
            telegram_config = config.get('telegram_cron', {})
            
            return {
                'enabled': telegram_config.get('enabled', True),
                'greeting_message': telegram_config.get('greeting_message', ''),
                'send_on_startup': telegram_config.get('send_on_startup', False),
                'max_users_per_batch': telegram_config.get('max_users_per_batch', 50),
                'delay_between_messages': telegram_config.get('delay_between_messages', 0.3),
                'skip_inactive_hours': telegram_config.get('skip_inactive_hours', True),
                'inactive_hours_start': telegram_config.get('inactive_hours_start', 22),
                'inactive_hours_end': telegram_config.get('inactive_hours_end', 8)
            }
        except Exception as e:
            logger.error(f"Error getting Telegram cron config: {e}")
            return {}


# Function for quick cron system setup
async def setup_cron_for_bot(bot, user_sessions, config_path: Optional[str] = None) -> Optional[TelegramGreetingCron]:
    """
    Quick setup of cron system for bot.
    
    :param bot: aiogram Bot instance
    :param user_sessions: User sessions module
    :param config_path: Path to configuration file
    :return: TelegramGreetingCron instance or None on error
    """
    logger.info("Setting up cron system for bot...")
    
    try:
        # Create cron manager instance
        cron_manager = TelegramGreetingCron(bot, user_sessions)
        
        # Check cron availability
        if not cron_manager.is_cron_enabled():
            logger.warning("Cron disabled in system or unavailable")
            return cron_manager
        
        # Initialize cron
        initialized = cron_manager.init_cron(config_path)
        
        if not initialized:
            logger.warning("Failed to initialize cron system")
            return cron_manager
        
        # Start greetings task
        started = cron_manager.start_greetings_cron()
        
        if started:
            logger.info("Cron system successfully set up and started")
        else:
            logger.warning("Cron system initialized but tasks not started")
        
        return cron_manager
        
    except Exception as e:
        logger.error(f"Error setting up cron system: {e}")
        return None


# Function to get cron system status
def get_cron_status(cron_manager: Optional[TelegramGreetingCron] = None) -> Dict[str, Any]:
    """
    Get cron system status.
    
    :param cron_manager: TelegramGreetingCron instance (optional)
    :return: Dictionary with status
    """
    if cron_manager:
        return cron_manager.get_status()
    
    # If manager not provided, try to get basic status
    try:
        from cron import get_cron_status as get_cron_system_status
        return get_cron_system_status()
    except ImportError:
        return {"status": "cron_module_not_available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}