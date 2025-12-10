import logging
import os

# Ensure the 'logs' directory exists to store log files.
# The 'exist_ok=True' argument prevents an error if the directory already exists.
os.makedirs("logs", exist_ok=True)

# Configure the root logger with the following settings:
# - Log level: INFO (includes INFO, WARNING, ERROR, CRITICAL)
# - Format: includes timestamp, log level, logger name, and the actual message
# - Handlers:
#     * FileHandler: writes logs to 'logs/server.log' using UTF-8 encoding
#     * StreamHandler: outputs logs to the console (stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def get_logger(name: str):
    """
    Retrieve a named logger instance configured with the global settings.

    This function returns a logger object that uses the logging configuration
    established by `logging.basicConfig()`. Each logger is identified by a `name`,
    which typically corresponds to the module or component generating the logs.
    Using distinct names helps in tracing the source of log messages, especially
    in larger applications with multiple modules.

    :param name: (str) The name of the logger.
                 Common practice is to use `__name__` when calling this function
                 from within a module (e.g., `logger = get_logger(__name__)`).
    :return: (logging.Logger) A configured logger instance associated with the given name.

    Usage example:
        >>> logger = get_logger(__name__)
        >>> logger.info("This is an informational message.")
        # This will print to both the console and 'logs/server.log'
    """
    return logging.getLogger(name)