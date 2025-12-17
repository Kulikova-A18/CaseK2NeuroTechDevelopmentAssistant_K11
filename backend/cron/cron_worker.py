"""
Основной класс cron-воркера, адаптированный под вашу систему.
"""

import os
import yaml
import logging
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class CronWorker:
    """Крон-воркер для вашей системы управления задачами."""
    
    def __init__(self, config_path: str = None):
        """
        Инициализация воркера.
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        if config_path is None:
            # Определяем путь относительно этого файла
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config.yaml')
        
        self.config_path = config_path
        self.config = self._load_config()
        self.scheduler = None
        self.tasks_instance = None
        
        logger.info(f"CronWorker инициализирован с конфигом: {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации с подстановкой переменных окружения."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Подстановка переменных окружения в формате ${VAR}
            import re
            def replace_env(match):
                var_name = match.group(1)
                # Поддерживаем значения по умолчанию: ${VAR:default}
                if ':' in var_name:
                    var_name, default = var_name.split(':', 1)
                else:
                    default = None
                
                value = os.environ.get(var_name)
                if value is not None:
                    return value
                elif default is not None:
                    return default
                else:
                    logger.warning(f"Переменная окружения {var_name} не найдена")
                    return match.group(0)  # Оставляем как есть
            
            content = re.sub(r'\${([^}]+)}', replace_env, content)
            
            return yaml.safe_load(content) or {}
            
        except FileNotFoundError:
            logger.error(f"Файл конфигурации не найден: {self.config_path}")
            return {"cron": {"jobs": {}}}
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return {"cron": {"jobs": {}}}
    
    def init_tasks(self, tasks_instance):
        """Инициализация экземпляра с задачами."""
        self.tasks_instance = tasks_instance
        logger.info("Экземпляр задач инициализирован")
    
    def setup_scheduler(self):
        """Настройка планировщика."""
        scheduler_config = self.config.get('scheduler', {})
        
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(
                max_workers=scheduler_config.get('thread_pool_size', 5)
            )
        }
        
        job_defaults = {
            'coalesce': scheduler_config.get('coalesce', True),
            'max_instances': 3,
            'misfire_grace_time': scheduler_config.get('misfire_grace_time', 600)
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=scheduler_config.get('timezone', 'UTC')
        )
        
        logger.info("Планировщик настроен")
    
    def add_jobs(self):
        """Добавление задач в планировщик."""
        if not self.tasks_instance:
            logger.error("Экземпляр задач не инициализирован")
            return
        
        jobs_config = self.config.get('cron', {}).get('jobs', {})
        
        for job_name, job_config in jobs_config.items():
            if not job_config.get('enabled', False):
                logger.info(f"Задача '{job_name}' отключена")
                continue
            
            task_name = job_config.get('task')
            schedule = job_config.get('schedule')
            
            if not task_name or not schedule:
                logger.warning(f"Некорректная конфигурация задачи '{job_name}'")
                continue
            
            # Получаем метод задачи
            task_method = getattr(self.tasks_instance, task_name, None)
            if not task_method:
                logger.warning(f"Метод задачи '{task_name}' не найден")
                continue
            
            try:
                # Добавляем задачу в планировщик
                job = self.scheduler.add_job(
                    func=task_method,
                    trigger=CronTrigger.from_crontab(schedule),
                    id=job_name,
                    name=job_name,
                    replace_existing=True
                )
                
                logger.info(f"✅ Задача '{job_name}' добавлена: {schedule}")
                
            except Exception as e:
                logger.error(f"Ошибка добавления задачи '{job_name}': {e}")
    
    def start(self):
        """Запуск планировщика."""
        if not self.scheduler:
            self.setup_scheduler()
            self.add_jobs()
        
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Планировщик cron задач запущен")
            
            # Выводим список активных задач
            jobs = self.scheduler.get_jobs()
            logger.info(f"Активных задач: {len(jobs)}")
            for job in jobs:
                logger.info(f"  - {job.name} ({job.id}): {job.trigger}")
    
    def stop(self):
        """Остановка планировщика."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("🛑 Планировщик cron задач остановлен")
    
    def run_task_now(self, task_name: str) -> Any:
        """
        Немедленный запуск задачи.
        
        Args:
            task_name: Имя метода задачи
            
        Returns:
            Результат выполнения задачи
        """
        if not self.tasks_instance:
            logger.error("Экземпляр задач не инициализирован")
            return None
        
        task_method = getattr(self.tasks_instance, task_name, None)
        if not task_method:
            logger.error(f"Задача '{task_name}' не найдена")
            return None
        
        logger.info(f"🚀 Немедленный запуск задачи: {task_name}")
        try:
            return task_method()
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи '{task_name}': {e}")
            return None
    
    def get_jobs_info(self) -> Dict[str, Any]:
        """Получение информации о задачах."""
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