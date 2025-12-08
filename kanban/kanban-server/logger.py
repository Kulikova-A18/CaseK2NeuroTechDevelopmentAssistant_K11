# logger.py
import logging
import os

def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO):
    """
    Configures and returns a logger instance that writes to both console and file.

    :param name: Name of the logger (typically the module name).
    :param log_file: Path to the log file. Default is "app.log".
    :param level: Logging level (e.g., logging.INFO, logging.DEBUG).
    :return: Configured logger instance.
    """
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger