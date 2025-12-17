"""
Скрипт запуска cron-воркера.
Может запускаться как отдельный процесс или интегрироваться в app.py.
"""

import sys
import os
import signal
import logging
from pathlib import Path

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from cron.cron_worker import CronWorker
from cron.tasks import create_cron_tasks

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cron_worker.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска."""
    logger.info("🚀 Запуск cron-воркера системы управления задачами")
    
    try:
        # Создаем экземпляр задач
        cron_tasks = create_cron_tasks()
        
        # Создаем и настраиваем воркер
        worker = CronWorker()
        worker.init_tasks(cron_tasks)
        
        # Обработчики сигналов для корректного завершения
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, останавливаюсь...")
            worker.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запускаем воркер
        worker.start()
        
        # Бесконечный цикл (или интеграция с вашим приложением)
        logger.info("Cron-воркер работает. Ctrl+C для остановки.")
        
        # Держим процесс активным
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


def run_as_thread():
    """
    Запуск воркера в отдельном потоке.
    Использовать для интеграции с вашим app.py.
    """
    import threading
    
    def worker_thread():
        try:
            cron_tasks = create_cron_tasks()
            worker = CronWorker()
            worker.init_tasks(cron_tasks)
            worker.start()
        except Exception as e:
            logger.error(f"Ошибка в потоке cron-воркера: {e}")
    
    thread = threading.Thread(target=worker_thread, daemon=True)
    thread.start()
    logger.info("Cron-воркер запущен в отдельном потоке")
    return thread


if __name__ == "__main__":
    # Запуск как самостоятельного процесса
    main()