"""
Cron task management module for Task Management System.
Provides scheduled task execution with configuration from config.yaml.
This module can be called without parameters for default setup.
"""

import os
import sys
import logging
import threading
import signal
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import yaml
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    from modules.csv_manager import CSVDataManager
    from modules.cache_manager import CacheManager
    from modules.constants import SystemConstants
    from modules.config_manager import ConfigManager

    LIBS_AVAILABLE = True
except ImportError as e:
    logging.error(f"Required libraries not available: {e}")
    LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CronTaskManager:
    """
    Main cron task manager for scheduled operations.

    param config_path: Path to configuration file (default: config.yaml in root directory)
    param auto_start: Whether to automatically start scheduler on initialization
    """

    def __init__(self, config_path: Optional[str] = None, auto_start: bool = True):
        if not LIBS_AVAILABLE:
            logger.warning("Cron functionality disabled due to missing dependencies")
            self.enabled = False
            return

        self.enabled = True
        self.scheduler = None
        self.tasks_instance = None

        # Determine configuration file path
        if config_path is None:
            # Default path: config.yaml in project root
            current_dir = Path(__file__).parent.parent
            config_path = str(current_dir / 'config.yaml')

        self.config_path = config_path
        self.config = self._load_config()

        # Initialize task dependencies
        self._init_dependencies()

        logger.info(f"CronTaskManager initialized with config: {config_path}")

        if auto_start:
            self.start()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file with environment variable substitution.

        return: Configuration dictionary
        """
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Configuration file not found: {self.config_path}")
                return {"cron": {"jobs": {}}, "scheduler": {}}

            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Substitute environment variables in format ${VAR} or ${VAR:default}
            import re

            def replace_env(match):
                """
                Replace environment variable placeholder with actual value.

                param match: Regex match object
                return: Substituted value
                """
                var_spec = match.group(1)

                # Handle default values: ${VAR:default}
                if ':' in var_spec:
                    var_name, default_value = var_spec.split(':', 1)
                else:
                    var_name, default_value = var_spec, None

                # Get value from environment
                env_value = os.environ.get(var_name)

                if env_value is not None:
                    return env_value
                elif default_value is not None:
                    return default_value
                else:
                    logger.warning(f"Environment variable {var_name} not found")
                    return match.group(0)  # Keep original placeholder

            # Replace all ${...} patterns
            content = re.sub(r'\${([^}]+)}', replace_env, content)

            # Parse YAML
            config = yaml.safe_load(content) or {}

            # Ensure cron section exists
            if 'cron' not in config:
                config['cron'] = {"jobs": {}}

            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in config file: {e}")
            return {"cron": {"jobs": {}}, "scheduler": {}}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {"cron": {"jobs": {}}, "scheduler": {}}

    def _init_dependencies(self):
        """Initialize task dependencies (CSV managers, cache, etc.)."""
        try:
            # Get configuration
            config_manager = ConfigManager()

            # Initialize tasks manager
            self.tasks_manager = CSVDataManager(
                SystemConstants.CSV_PATHS['tasks'],
                SystemConstants.TASKS_SCHEMA
            )

            # Initialize cache if enabled
            cache_enabled = config_manager.get('performance.cache_enabled', True)
            cache_ttl = config_manager.get('performance.cache_ttl_seconds',
                                          SystemConstants.DEFAULT_CACHE_TTL_SECONDS)

            self.cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)

            logger.info("Task dependencies initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing dependencies: {e}")
            # Create minimal fallback
            self.tasks_manager = None
            self.cache_manager = None

    def check_deadlines(self):
        """
        Check task deadlines and log notifications.

        return: Dictionary with deadline information
        """
        try:
            if not self.tasks_manager:
                logger.error("Tasks manager not available for deadline check")
                return {"error": "Tasks manager not available"}

            from datetime import datetime

            logger.info("Checking task deadlines...")

            # This is a simplified example - implement your actual deadline logic
            all_tasks = self.tasks_manager.read_all()
            overdue_count = 0
            due_today_count = 0

            for task in all_tasks:
                # Add your deadline checking logic here
                pass

            result = {
                "timestamp": datetime.now().isoformat(),
                "overdue_tasks": overdue_count,
                "due_today": due_today_count,
                "total_tasks": len(all_tasks)
            }

            logger.info(f"Deadline check completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in deadline check: {e}")
            return {"error": str(e)}

    def generate_daily_report(self):
        """
        Generate daily activity report.

        return: Dictionary with daily report data
        """
        try:
            logger.info("Generating daily report...")

            # Implement your report generation logic
            from datetime import datetime

            result = {
                "timestamp": datetime.now().isoformat(),
                "report_date": datetime.now().strftime('%Y-%m-%d'),
                "tasks_processed": 0,
                "status": "completed"
            }

            logger.info(f"Daily report generated: {result}")
            return result

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return {"error": str(e)}

    def cleanup_cache(self):
        """
        Clean up outdated cache entries.

        return: Dictionary with cleanup results
        """
        try:
            logger.info("Cleaning up cache...")

            if not self.cache_manager:
                return {"status": "skipped", "reason": "Cache not enabled"}

            # Implement cache cleanup logic
            # Example: self.cache_manager.cleanup()

            result = {
                "timestamp": datetime.now().isoformat(),
                "cleaned_items": 0,
                "status": "completed"
            }

            logger.info(f"Cache cleanup completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            return {"error": str(e)}

    def sync_telegram_status(self):
        """
        Synchronize status with Telegram.

        return: Dictionary with sync results
        """
        try:
            logger.info("Synchronizing with Telegram...")

            # Implement Telegram sync logic
            # Check if Telegram is configured
            telegram_enabled = self.config.get('telegram', {}).get('bot_token')

            if not telegram_enabled:
                return {"status": "skipped", "reason": "Telegram not configured"}

            result = {
                "timestamp": datetime.now().isoformat(),
                "synced_messages": 0,
                "status": "completed"
            }

            logger.info(f"Telegram sync completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error syncing with Telegram: {e}")
            return {"error": str(e)}

    def _setup_scheduler(self):
        """Initialize and configure the task scheduler."""
        try:
            scheduler_config = self.config.get('scheduler', {})

            # Configure job stores
            jobstores = {
                'default': MemoryJobStore()
            }

            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(
                    max_workers=scheduler_config.get('thread_pool_size', 5)
                )
            }

            # Configure job defaults
            job_defaults = {
                'coalesce': scheduler_config.get('coalesce', True),
                'max_instances': 3,
                'misfire_grace_time': scheduler_config.get('misfire_grace_time', 600)
            }

            # Create scheduler
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=scheduler_config.get('timezone', 'UTC')
            )

            logger.info("Task scheduler configured")

        except Exception as e:
            logger.error(f"Error setting up scheduler: {e}")
            self.scheduler = None

    def _add_scheduled_jobs(self):
        """Add scheduled jobs based on configuration."""
        try:
            if not self.scheduler:
                logger.error("Scheduler not initialized")
                return

            jobs_config = self.config.get('cron', {}).get('jobs', {})

            # Map task names to methods
            task_methods = {
                'check_deadlines': self.check_deadlines,
                'generate_daily_report': self.generate_daily_report,
                'cleanup_cache': self.cleanup_cache,
                'sync_telegram_status': self.sync_telegram_status,
            }

            for job_name, job_config in jobs_config.items():
                if not job_config.get('enabled', False):
                    logger.info(f"Job '{job_name}' is disabled")
                    continue

                task_name = job_config.get('task')
                schedule = job_config.get('schedule')

                if not task_name or not schedule:
                    logger.warning(f"Invalid configuration for job '{job_name}'")
                    continue

                # Get task method
                task_method = task_methods.get(task_name)
                if not task_method:
                    logger.warning(f"Task method '{task_name}' not found")
                    continue

                try:
                    # Add job to scheduler
                    job = self.scheduler.add_job(
                        func=task_method,
                        trigger=CronTrigger.from_crontab(schedule),
                        id=job_name,
                        name=job_name,
                        replace_existing=True
                    )

                    logger.info(f"Job '{job_name}' scheduled: {schedule}")

                except Exception as e:
                    logger.error(f"Error scheduling job '{job_name}': {e}")

            # Log all scheduled jobs
            jobs = self.scheduler.get_jobs()
            logger.info(f"Total scheduled jobs: {len(jobs)}")

        except Exception as e:
            logger.error(f"Error adding scheduled jobs: {e}")

    def start(self):
        """
        Start the cron task scheduler.

        return: True if started successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.warning("Cron functionality is disabled")
                return False

            if not self.scheduler:
                self._setup_scheduler()
                self._add_scheduled_jobs()

            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                logger.info("Cron task scheduler started")

                # Log active jobs
                jobs = self.scheduler.get_jobs()
                logger.info(f"Active scheduled jobs: {len(jobs)}")

                return True
            else:
                logger.info("Scheduler already running")
                return True

        except Exception as e:
            logger.error(f"Error starting cron scheduler: {e}")
            return False

    def stop(self):
        """
        Stop the cron task scheduler.

        return: True if stopped successfully, False otherwise
        """
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Cron task scheduler stopped")
                return True
            else:
                logger.info("Scheduler not running")
                return True

        except Exception as e:
            logger.error(f"Error stopping cron scheduler: {e}")
            return False

    def get_job_info(self):
        """
        Get information about scheduled jobs.

        return: Dictionary with job information
        """
        try:
            if not self.scheduler:
                return {"scheduler": "not_initialized"}

            jobs = self.scheduler.get_jobs()

            return {
                "running": self.scheduler.running,
                "job_count": len(jobs),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": str(job.next_run_time) if job.next_run_time else None,
                        "trigger": str(job.trigger)
                    }
                    for job in jobs
                ]
            }

        except Exception as e:
            logger.error(f"Error getting job info: {e}")
            return {"error": str(e)}

    def run_job_now(self, job_name: str):
        """
        Run a specific job immediately.

        param job_name: Name of the job to run
        return: Job execution result or None
        """
        try:
            # Map job names to methods
            job_methods = {
                'check_deadlines': self.check_deadlines,
                'generate_daily_report': self.generate_daily_report,
                'cleanup_cache': self.cleanup_cache,
                'sync_telegram_status': self.sync_telegram_status,
            }

            method = job_methods.get(job_name)
            if not method:
                logger.error(f"Job '{job_name}' not found")
                return None

            logger.info(f"Running job '{job_name}' immediately")
            return method()

        except Exception as e:
            logger.error(f"Error running job '{job_name}': {e}")
            return None

    def is_enabled(self) -> bool:
        """
        Check if cron functionality is enabled.

        return: True if cron is enabled, False otherwise
        """
        return self.enabled

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        return: True if scheduler is running, False otherwise
        """
        return self.scheduler is not None and self.scheduler.running


# Global instance for easy access
_global_cron_manager = None


def get_cron_manager(config_path: Optional[str] = None) -> CronTaskManager:
    """
    Get or create global cron manager instance.

    param config_path: Optional path to configuration file
    return: CronTaskManager instance
    """
    global _global_cron_manager

    if _global_cron_manager is None:
        _global_cron_manager = CronTaskManager(config_path=config_path, auto_start=True)

    return _global_cron_manager


def start_cron_scheduler(config_path: Optional[str] = None) -> bool:
    """
    Start cron scheduler with default configuration.
    Call this function without parameters to start cron tasks.

    param config_path: Optional path to configuration file
    return: True if started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start()

    except Exception as e:
        logger.error(f"Error starting cron scheduler: {e}")
        return False


def stop_cron_scheduler() -> bool:
    """
    Stop cron scheduler.

    return: True if stopped successfully, False otherwise
    """
    try:
        if _global_cron_manager:
            return _global_cron_manager.stop()
        else:
            logger.info("Cron scheduler not initialized")
            return True

    except Exception as e:
        logger.error(f"Error stopping cron scheduler: {e}")
        return False


def run_cron_job(job_name: str):
    """
    Run a specific cron job immediately.

    param job_name: Name of the job to run
    return: Job execution result or None
    """
    try:
        manager = get_cron_manager()
        return manager.run_job_now(job_name)

    except Exception as e:
        logger.error(f"Error running cron job '{job_name}': {e}")
        return None


def get_cron_status():
    """
    Get status of cron scheduler.

    return: Dictionary with cron scheduler status
    """
    try:
        if _global_cron_manager:
            return _global_cron_manager.get_job_info()
        else:
            return {"status": "not_initialized"}

    except Exception as e:
        logger.error(f"Error getting cron status: {e}")
        return {"error": str(e)}


def init_cron_in_background(config_path: Optional[str] = None):
    """
    Initialize cron scheduler in background thread.
    Use this for integration with Flask/Django apps.

    param config_path: Optional path to configuration file
    return: Thread object or None
    """
    try:
        def run_scheduler():
            try:
                manager = CronTaskManager(config_path=config_path, auto_start=True)
                # Keep thread alive
                import time
                while True:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Background cron thread error: {e}")

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()

        logger.info("Cron scheduler started in background thread")
        return thread

    except Exception as e:
        logger.error(f"Error initializing cron in background: {e}")
        return None


# # Demo/test function
# def demo_cron_functionality():
#     """
#     Demonstrate cron functionality.
#     Call this to test cron features.
#     """
#     print("Testing Cron Task Manager...")
#
#     # Start cron scheduler
#     if start_cron_scheduler():
#         print("✓ Cron scheduler started")
#
#         # Get status
#         status = get_cron_status()
#         print(f"✓ Cron status: {status}")
#
#         # Run a job manually
#         result = run_cron_job('check_deadlines')
#         print(f"✓ Manual job execution: {result}")
#
#         # Wait a bit
#         import time
#         time.sleep(2)
#
#         # Stop scheduler
#         if stop_cron_scheduler():
#             print("✓ Cron scheduler stopped")
#         else:
#             print("✗ Failed to stop cron scheduler")
#     else:
#         print("✗ Failed to start cron scheduler")
#
#
# if __name__ == "__main__":
#     # Configure logging for standalone execution
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
#
#     # Run demo if executed directly
#     demo_cron_functionality()
