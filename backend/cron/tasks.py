"""
Конкретные задачи для cron-воркера.
Интегрированы с существующей системой.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from modules.csv_manager import CSVDataManager
from modules.cache_manager import CacheManager
from modules.constants import SystemConstants

logger = logging.getLogger(__name__)


class CronTasks:
    """Класс с задачами для cron-воркера."""
    
    def __init__(self, tasks_manager: CSVDataManager = None, 
                 users_manager: CSVDataManager = None,
                 cache_manager: CacheManager = None):
        """
        Инициализация с зависимостями вашей системы.
        
        Args:
            tasks_manager: Менеджер задач из вашей системы
            users_manager: Менеджер пользователей
            cache_manager: Менеджер кэша
        """
        self.tasks_manager = tasks_manager
        self.users_manager = users_manager
        self.cache_manager = cache_manager
        
        # Если не переданы, создаем самостоятельно
        if not self.tasks_manager:
            self.tasks_manager = CSVDataManager(
                SystemConstants.CSV_PATHS['tasks'],
                SystemConstants.TASKS_SCHEMA
            )
        
        logger.info("CronTasks инициализирован")
    
    # =============== ОСНОВНЫЕ ЗАДАЧИ ===============
    
    def check_deadlines(self) -> Dict[str, Any]:
        """Проверка дедлайнов задач и отправка уведомлений."""
        logger.info("🔔 Проверка дедлайнов задач...")
        
        try:
            all_tasks = self.tasks_manager.read_all()
            today = datetime.now().date()
            overdue_tasks = []
            due_today_tasks = []
            
            for task in all_tasks:
                due_date_str = task.get('due_date')
                if not due_date_str:
                    continue
                
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    status = task.get('status', '')
                    
                    # Просроченные
                    if due_date < today and status != 'done':
                        overdue_tasks.append(task)
                    
                    # На сегодня
                    elif due_date == today and status not in ['done', 'in_progress']:
                        due_today_tasks.append(task)
                        
                except ValueError:
                    continue
            
            # Формируем отчет
            result = {
                "timestamp": datetime.now().isoformat(),
                "overdue_count": len(overdue_tasks),
                "due_today_count": len(due_today_tasks),
                "overdue_tasks": [t.get('task_id') for t in overdue_tasks[:5]],
                "due_today_tasks": [t.get('task_id') for t in due_today_tasks[:5]]
            }
            
            # Здесь можно добавить отправку в Telegram
            if overdue_tasks or due_today_tasks:
                logger.warning(f"Найдено {len(overdue_tasks)} просроченных и {len(due_today_tasks)} задач на сегодня")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка проверки дедлайнов: {e}")
            return {"error": str(e)}
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Генерация ежедневного отчета по активности."""
        logger.info("📊 Генерация ежедневного отчета...")
        
        try:
            all_tasks = self.tasks_manager.read_all()
            
            # Статистика
            total_tasks = len(all_tasks)
            completed_today = 0
            created_today = 0
            
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            for task in all_tasks:
                # Завершенные сегодня
                completed_at = task.get('completed_at', '')
                if completed_at.startswith(today_str):
                    completed_today += 1
                
                # Созданные сегодня
                created_at = task.get('created_at', '')
                if created_at.startswith(today_str):
                    created_today += 1
            
            result = {
                "date": today_str,
                "total_tasks": total_tasks,
                "completed_today": completed_today,
                "created_today": created_today,
                "completion_rate": f"{(completed_today/max(created_today, 1))*100:.1f}%" if created_today > 0 else "0%"
            }
            
            logger.info(f"Отчет сгенерирован: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            return {"error": str(e)}
    
    def cleanup_cache(self) -> Dict[str, Any]:
        """Очистка устаревшего кэша."""
        logger.info("🧹 Очистка кэша...")
        
        if not self.cache_manager:
            return {"status": "skipped", "reason": "Cache manager not available"}
        
        try:
            # Здесь логика очистки специфичного для вашего CacheManager
            # Например, удаление старых ключей
            
            # Имитация очистки
            cleaned = 0
            # Реальная реализация зависит от вашего cache_manager
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cleaned_items": cleaned,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            return {"error": str(e)}
    
    def weekly_llm_analysis(self) -> Dict[str, Any]:
        """Еженедельный AI-анализ активности."""
        logger.info("🤖 Запуск еженедельного LLM анализа...")
        
        # Используем существующий LLM API из вашей системы
        # или заглушку для демо
        
        return {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "weekly",
            "status": "demo_mode",
            "note": "В реальной системе здесь будет вызов вашего LLM API"
        }
    
    def sync_telegram_status(self) -> Dict[str, Any]:
        """Синхронизация статусов с Telegram."""
        logger.info("🔄 Синхронизация с Telegram...")
        
        # Здесь можно добавить логику синхронизации
        # между задачами в системе и Telegram
        
        return {
            "timestamp": datetime.now().isoformat(),
            "synced_items": 0,
            "status": "completed"
        }
    
    # =============== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===============
    
    def test_connection(self) -> Dict[str, Any]:
        """Тестовая задача для проверки работы."""
        logger.info("🧪 Тестовая задача выполняется...")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "message": "Cron worker is working!",
            "system_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Фабрика для создания экземпляра с зависимостями
def create_cron_tasks():
    """Создает экземпляр CronTasks с зависимостями."""
    # Импортируем здесь, чтобы избежать циклических зависимостей
    from modules.csv_manager import CSVDataManager
    from modules.cache_manager import CacheManager
    from modules.constants import SystemConstants
    from modules.config_manager import ConfigManager
    
    config_manager = ConfigManager()
    
    # Создаем менеджеры
    tasks_manager = CSVDataManager(
        SystemConstants.CSV_PATHS['tasks'],
        SystemConstants.TASKS_SCHEMA
    )
    
    cache_enabled = config_manager.get('performance.cache_enabled', True)
    cache_ttl = config_manager.get('performance.cache_ttl_seconds', 
                                  SystemConstants.DEFAULT_CACHE_TTL_SECONDS)
    
    cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)
    
    return CronTasks(
        tasks_manager=tasks_manager,
        cache_manager=cache_manager
    )