"""
Cron task management module for Task Management System.
Provides scheduled task execution with configuration from config.yaml.
This module can be called without parameters for default setup.
"""

import os
import sys
import logging
import threading
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import yaml
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
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
        self.job_methods = {}  # Store job methods for individual control
        
        # Default constants for fallback
        self.default_constants = {
            'csv_paths': {
                'tasks': './data/tasks.csv',
                'users': './data/users.csv',
                'logs': './data/logs.csv'
            },
            'cache_ttl': 300,  # 5 minutes in seconds
            'tasks_schema': ['id', 'title', 'description', 'status', 'deadline', 'priority']
        }

        # Determine configuration file path
        if config_path is None:
            # Default path: config.yaml in project root
            current_dir = Path(__file__).parent.parent
            config_path = str(current_dir / 'config.yaml')

        self.config_path = config_path
        self.config = self._load_config()
        
        # Check if cron is globally disabled in config
        cron_enabled = self.config.get('cron', {}).get('enabled', True)
        if not cron_enabled:
            logger.info("Cron is globally disabled in config.yaml (cron.enabled: false)")
            self.enabled = False
            return

        # Initialize task dependencies
        self._init_dependencies()

        # Initialize job methods mapping
        self._init_job_methods()

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
                return {"cron": {"jobs": {}, "enabled": True}, "scheduler": {}}

            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()

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

            # Ensure cron section exists with enabled flag
            if 'cron' not in config:
                config['cron'] = {"jobs": {}, "enabled": True}
            elif 'enabled' not in config['cron']:
                config['cron']['enabled'] = True

            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in config file: {e}")
            return {"cron": {"jobs": {}, "enabled": True}, "scheduler": {}}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {"cron": {"jobs": {}, "enabled": True}, "scheduler": {}}

    def _init_dependencies(self):
        """Initialize task dependencies."""
        try:
            # Initialize simple data structures for demonstration
            # In a real system, these would be your actual managers
            self.tasks_manager = self._create_simple_task_manager()
            self.cache_manager = self._create_simple_cache_manager()
            
            logger.info("Task dependencies initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing dependencies: {e}")
            # Create minimal fallback
            self.tasks_manager = None
            self.cache_manager = None

    def _create_simple_task_manager(self):
        """Create a simple task manager for demonstration."""
        class SimpleTaskManager:
            def __init__(self, csv_path, schema):
                self.csv_path = csv_path
                self.schema = schema
                
            def read_all(self):
                """Read all tasks from CSV file."""
                try:
                    if os.path.exists(self.csv_path):
                        import csv
                        with open(self.csv_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            return list(reader)
                    return []
                except Exception as e:
                    logger.error(f"Error reading tasks: {e}")
                    return []
                    
            def get_count(self):
                """Get total task count."""
                tasks = self.read_all()
                return len(tasks)
                
        # Get CSV path from config or use default
        csv_path = self.config.get('data', {}).get('tasks_csv_path', 
                   self.default_constants['csv_paths']['tasks'])
        
        return SimpleTaskManager(
            csv_path,
            self.default_constants['tasks_schema']
        )

    def _create_simple_cache_manager(self):
        """Create a simple cache manager for demonstration."""
        class SimpleCacheManager:
            def __init__(self, enabled=True, ttl=300):
                self.enabled = enabled
                self.ttl = ttl
                self.cache = {}
                
            def get(self, key):
                """Get value from cache."""
                if not self.enabled:
                    return None
                    
                if key in self.cache:
                    value, timestamp = self.cache[key]
                    if datetime.now().timestamp() - timestamp < self.ttl:
                        return value
                    else:
                        del self.cache[key]
                return None
                
            def set(self, key, value):
                """Set value in cache."""
                if not self.enabled:
                    return
                self.cache[key] = (value, datetime.now().timestamp())
                
            def cleanup(self):
                """Clean up expired cache entries."""
                if not self.enabled:
                    return 0
                    
                current_time = datetime.now().timestamp()
                expired_keys = [
                    key for key, (_, timestamp) in self.cache.items()
                    if current_time - timestamp >= self.ttl
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                    
                return len(expired_keys)
        
        # Get cache settings from config
        cache_enabled = self.config.get('performance', {}).get('cache_enabled', True)
        cache_ttl = self.config.get('performance', {}).get('cache_ttl_seconds', 
                  self.default_constants['cache_ttl'])
        
        return SimpleCacheManager(enabled=cache_enabled, ttl=cache_ttl)

    def _init_job_methods(self):
        """Initialize mapping of job names to methods."""
        self.job_methods = {
            'check_deadlines': self.check_deadlines,
            'generate_daily_report': self.generate_daily_report,
            'cleanup_cache': self.cleanup_cache,
            'sync_telegram_status': self.sync_telegram_status,
            'weekly_llm_analysis': self.weekly_llm_analysis,
        }

    def check_deadlines(self):
        """
        Check task deadlines and log notifications.

        return: Dictionary with deadline information
        """
        try:
            if not self.tasks_manager:
                logger.error("Tasks manager not available for deadline check")
                return {"error": "Tasks manager not available"}

            logger.info("Checking task deadlines...")

            # Read tasks and check deadlines
            all_tasks = self.tasks_manager.read_all()
            overdue_count = 0
            due_today_count = 0
            now = datetime.now()

            for task in all_tasks:
                # Simple deadline checking logic
                if 'deadline' in task and task['deadline']:
                    try:
                        deadline_date = datetime.strptime(task['deadline'], '%Y-%m-%d')
                        days_until_deadline = (deadline_date - now).days
                        
                        if days_until_deadline < 0:
                            overdue_count += 1
                        elif days_until_deadline == 0:
                            due_today_count += 1
                    except (ValueError, TypeError):
                        continue

            result = {
                "timestamp": now.isoformat(),
                "overdue_tasks": overdue_count,
                "due_today": due_today_count,
                "total_tasks": len(all_tasks),
                "status": "completed"
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

            # Get task statistics
            task_count = 0
            if self.tasks_manager:
                task_count = self.tasks_manager.get_count()

            # Get cache statistics
            cache_cleaned = 0
            if self.cache_manager:
                cache_cleaned = self.cache_manager.cleanup()

            result = {
                "timestamp": datetime.now().isoformat(),
                "report_date": datetime.now().strftime('%Y-%m-%d'),
                "tasks_processed": task_count,
                "cache_cleaned": cache_cleaned,
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

            # Clean up cache
            cleaned_items = self.cache_manager.cleanup()

            result = {
                "timestamp": datetime.now().isoformat(),
                "cleaned_items": cleaned_items,
                "cache_size": len(self.cache_manager.cache),
                "status": "completed"
            }

            logger.info(f"Cache cleanup completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            return {"error": str(e)}

    def weekly_llm_analysis(self):
        """
        Perform weekly LLM activity analysis.

        return: Dictionary with analysis results
        """
        try:
            logger.info("Performing weekly LLM analysis...")

            # Check if LLM is enabled
            llm_enabled = self.config.get('llm', {}).get('enabled', False)
            if not llm_enabled:
                return {"status": "skipped", "reason": "LLM not enabled"}

            # Simulate LLM analysis
            result = {
                "timestamp": datetime.now().isoformat(),
                "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                "models_analyzed": 1,
                "analysis_type": "weekly_summary",
                "status": "completed"
            }

            logger.info(f"Weekly LLM analysis completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in weekly LLM analysis: {e}")
            return {"error": str(e)}

    def sync_telegram_status(self):
        """
        Synchronize status with Telegram.

        return: Dictionary with sync results
        """
        try:
            logger.info("Synchronizing with Telegram...")

            # Check if Telegram is configured
            telegram_enabled = self.config.get('telegram', {}).get('bot_token')
            if not telegram_enabled:
                return {"status": "skipped", "reason": "Telegram not configured"}

            # Simulate Telegram sync
            result = {
                "timestamp": datetime.now().isoformat(),
                "synced_messages": 0,
                "last_sync_time": datetime.now().isoformat(),
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
                task_method = self.job_methods.get(task_name)
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
            
            # Double-check config in case it was reloaded
            if not self.config.get('cron', {}).get('enabled', True):
                logger.info("Cron is disabled in configuration")
                self.enabled = False
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

    def start_deadline_notifications_cron_functionality(self) -> bool:
        """
        Start only the deadline notifications cron job.

        return: True if job started successfully, False otherwise
        """
        return self._start_specific_job('deadline_notifications')

    def start_daily_report_cron_functionality(self) -> bool:
        """
        Start only the daily report cron job.

        return: True if job started successfully, False otherwise
        """
        return self._start_specific_job('daily_report')

    def start_cache_cleanup_cron_functionality(self) -> bool:
        """
        Start only the cache cleanup cron job.

        return: True if job started successfully, False otherwise
        """
        return self._start_specific_job('cache_cleanup')

    def start_weekly_analysis_cron_functionality(self) -> bool:
        """
        Start only the weekly analysis cron job.

        return: True if job started successfully, False otherwise
        """
        return self._start_specific_job('weekly_analysis')

    def start_telegram_sync_cron_functionality(self) -> bool:
        """
        Start only the telegram sync cron job.

        return: True if job started successfully, False otherwise
        """
        return self._start_specific_job('telegram_sync')

    def _start_specific_job(self, job_name: str) -> bool:
        """
        Start a specific cron job.

        param job_name: Name of the job to start
        return: True if job started successfully, False otherwise
        """
        try:
            if not self.enabled:
                logger.warning(f"Cron is disabled, cannot start job '{job_name}'")
                return False

            # Ensure scheduler is initialized
            if not self.scheduler:
                self._setup_scheduler()
                if not self.scheduler:
                    logger.error(f"Cannot start job '{job_name}': scheduler not initialized")
                    return False

            # Get job configuration
            jobs_config = self.config.get('cron', {}).get('jobs', {})
            job_config = jobs_config.get(job_name)

            if not job_config:
                logger.error(f"Job configuration not found: '{job_name}'")
                return False

            if not job_config.get('enabled', False):
                logger.info(f"Job '{job_name}' is disabled in configuration")
                return False

            task_name = job_config.get('task')
            schedule = job_config.get('schedule')

            if not task_name or not schedule:
                logger.error(f"Invalid configuration for job '{job_name}'")
                return False

            # Get task method
            task_method = self.job_methods.get(task_name)
            if not task_method:
                logger.error(f"Task method '{task_name}' not found for job '{job_name}'")
                return False

            try:
                # Check if job already exists
                existing_job = self.scheduler.get_job(job_id=job_name)
                
                if existing_job:
                    # Remove existing job first
                    existing_job.remove()
                    logger.info(f"Removed existing job '{job_name}'")

                # Add new job
                job = self.scheduler.add_job(
                    func=task_method,
                    trigger=CronTrigger.from_crontab(schedule),
                    id=job_name,
                    name=job_name,
                    replace_existing=True
                )

                logger.info(f"Job '{job_name}' started with schedule: {schedule}")

                # Start scheduler if not running
                if not self.scheduler.running:
                    self.scheduler.start()
                    logger.info("Scheduler started for individual job")

                return True

            except Exception as e:
                logger.error(f"Error starting job '{job_name}': {e}")
                return False

        except Exception as e:
            logger.error(f"Error in _start_specific_job for '{job_name}': {e}")
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

    def stop_specific_job(self, job_name: str) -> bool:
        """
        Stop a specific cron job.

        param job_name: Name of the job to stop
        return: True if job stopped successfully, False otherwise
        """
        try:
            if not self.scheduler:
                logger.warning(f"Scheduler not initialized, cannot stop job '{job_name}'")
                return False

            job = self.scheduler.get_job(job_id=job_name)
            if job:
                job.remove()
                logger.info(f"Job '{job_name}' stopped")
                return True
            else:
                logger.warning(f"Job '{job_name}' not found")
                return False

        except Exception as e:
            logger.error(f"Error stopping job '{job_name}': {e}")
            return False

    def get_job_info(self):
        """
        Get information about scheduled jobs.

        return: Dictionary with job information
        """
        try:
            if not self.scheduler:
                if not self.enabled:
                    return {"status": "disabled", "enabled": False}
                return {"scheduler": "not_initialized", "enabled": True}

            jobs = self.scheduler.get_jobs()

            return {
                "enabled": True,
                "running": self.scheduler.running,
                "job_count": len(jobs),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": str(job.next_run_time) if job.next_run_time else None,
                        "trigger": str(job.trigger),
                        "enabled": True
                    }
                    for job in jobs
                ]
            }

        except Exception as e:
            logger.error(f"Error getting job info: {e}")
            return {"error": str(e)}

    def get_specific_job_info(self, job_name: str):
        """
        Get information about a specific job.

        param job_name: Name of the job to get info for
        return: Dictionary with job information
        """
        try:
            if not self.scheduler:
                return {"error": "Scheduler not initialized"}

            job = self.scheduler.get_job(job_id=job_name)
            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "enabled": True
                }
            else:
                # Check if job is disabled in config
                jobs_config = self.config.get('cron', {}).get('jobs', {})
                job_config = jobs_config.get(job_name)
                
                if job_config:
                    return {
                        "id": job_name,
                        "name": job_name,
                        "enabled": job_config.get('enabled', False),
                        "reason": "Disabled in configuration" if not job_config.get('enabled', False) else "Not scheduled"
                    }
                else:
                    return {"error": f"Job '{job_name}' not found"}

        except Exception as e:
            logger.error(f"Error getting job info for '{job_name}': {e}")
            return {"error": str(e)}

    def run_job_now(self, job_name: str):
        """
        Run a specific job immediately.

        param job_name: Name of the job to run
        return: Job execution result or None
        """
        try:
            if not self.enabled:
                logger.warning("Cron is disabled, cannot run jobs")
                return {"error": "Cron is disabled"}

            # Get job configuration to find task name
            jobs_config = self.config.get('cron', {}).get('jobs', {})
            job_config = jobs_config.get(job_name)
            
            if not job_config:
                logger.error(f"Job '{job_name}' not found in configuration")
                return None

            task_name = job_config.get('task')
            if not task_name:
                logger.error(f"No task specified for job '{job_name}'")
                return None

            # Get task method
            task_method = self.job_methods.get(task_name)
            if not task_method:
                logger.error(f"Task method '{task_name}' not found for job '{job_name}'")
                return None

            logger.info(f"Running job '{job_name}' immediately")
            return task_method()

        except Exception as e:
            logger.error(f"Error running job '{job_name}': {e}")
            return None

    def is_enabled(self) -> bool:
        """
        Check if cron functionality is enabled.

        return: True if cron is enabled, False otherwise
        """
        return self.enabled and self.config.get('cron', {}).get('enabled', True)

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        return: True if scheduler is running, False otherwise
        """
        return self.scheduler is not None and self.scheduler.running

    def reload_config(self):
        """
        Reload configuration from file.

        return: True if reloaded successfully, False otherwise
        """
        try:
            old_enabled = self.enabled
            self.config = self._load_config()
            
            # Check if cron status changed
            cron_enabled = self.config.get('cron', {}).get('enabled', True)
            if cron_enabled != old_enabled:
                self.enabled = cron_enabled
                if not cron_enabled and self.scheduler:
                    self.stop()
                    logger.info("Cron disabled via config reload, scheduler stopped")
                elif cron_enabled and not self.scheduler:
                    logger.info("Cron enabled via config reload, scheduler can be started")
            
            logger.info("Configuration reloaded")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            return False


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
        
        # Check if cron is enabled
        if not manager.is_enabled():
            logger.info("Cron scheduler is disabled, not starting")
            return False
            
        return manager.start()

    except Exception as e:
        logger.error(f"Error starting cron scheduler: {e}")
        return False


# Functions for starting individual cron jobs
def start_deadline_notifications_cron_functionality(config_path: Optional[str] = None) -> bool:
    """
    Start only the deadline notifications cron job.

    param config_path: Optional path to configuration file
    return: True if job started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start_deadline_notifications_cron_functionality()
    except Exception as e:
        logger.error(f"Error starting deadline notifications: {e}")
        return False


def start_daily_report_cron_functionality(config_path: Optional[str] = None) -> bool:
    """
    Start only the daily report cron job.

    param config_path: Optional path to configuration file
    return: True if job started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start_daily_report_cron_functionality()
    except Exception as e:
        logger.error(f"Error starting daily report: {e}")
        return False


def start_cache_cleanup_cron_functionality(config_path: Optional[str] = None) -> bool:
    """
    Start only the cache cleanup cron job.

    param config_path: Optional path to configuration file
    return: True if job started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start_cache_cleanup_cron_functionality()
    except Exception as e:
        logger.error(f"Error starting cache cleanup: {e}")
        return False


def start_weekly_analysis_cron_functionality(config_path: Optional[str] = None) -> bool:
    """
    Start only the weekly analysis cron job.

    param config_path: Optional path to configuration file
    return: True if job started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start_weekly_analysis_cron_functionality()
    except Exception as e:
        logger.error(f"Error starting weekly analysis: {e}")
        return False


def start_telegram_sync_cron_functionality(config_path: Optional[str] = None) -> bool:
    """
    Start only the telegram sync cron job.

    param config_path: Optional path to configuration file
    return: True if job started successfully, False otherwise
    """
    try:
        manager = get_cron_manager(config_path)
        return manager.start_telegram_sync_cron_functionality()
    except Exception as e:
        logger.error(f"Error starting telegram sync: {e}")
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
        
        # Check if cron is enabled
        if not manager.is_enabled():
            logger.warning("Cron is disabled, cannot run jobs")
            return {"error": "Cron is disabled"}
            
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
            return {"status": "not_initialized", "enabled": False}

    except Exception as e:
        logger.error(f"Error getting cron status: {e}")
        return {"error": str(e)}


def get_specific_cron_job_status(job_name: str):
    """
    Get status of a specific cron job.

    param job_name: Name of the job to check
    return: Dictionary with job status
    """
    try:
        if _global_cron_manager:
            return _global_cron_manager.get_specific_job_info(job_name)
        else:
            return {"status": "not_initialized", "job": job_name, "enabled": False}

    except Exception as e:
        logger.error(f"Error getting cron job status for '{job_name}': {e}")
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
                # Only keep thread alive if cron is enabled
                if manager.is_enabled():
                    import time
                    while True:
                        time.sleep(1)
                else:
                    logger.info("Cron disabled, background thread will exit")
            except Exception as e:
                logger.error(f"Background cron thread error: {e}")

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()

        logger.info("Cron scheduler started in background thread")
        return thread

    except Exception as e:
        logger.error(f"Error initializing cron in background: {e}")
        return None


def is_cron_enabled(config_path: Optional[str] = None) -> bool:
    """
    Check if cron is enabled in configuration.

    param config_path: Optional path to configuration file
    return: True if cron is enabled, False otherwise
    """
    try:
        # Load config directly to check without initializing manager
        if config_path is None:
            current_dir = Path(__file__).parent.parent
            config_path = str(current_dir / 'config.yaml')
            
        if not os.path.exists(config_path):
            return False
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            
        return config.get('cron', {}).get('enabled', True)
        
    except Exception as e:
        logger.error(f"Error checking cron status: {e}")
        return False
