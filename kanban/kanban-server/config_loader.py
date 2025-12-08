# config_loader.py
import yaml
import os
from flask import Flask

from logger import setup_logger
from storage import InMemoryStorage

# Import entity modules
from modules.tasks import make_tasks_handlers
from modules.docs import make_docs_handlers
from modules.events import make_events_handlers
from modules.telegram import make_telegram_handlers


def load_routes(app: Flask, yaml_path: str):
    """
    Loads API routes from a YAML configuration file and registers them with the Flask app.

    :param app: Flask application instance.
    :param yaml_path: Path to the YAML configuration file.
    :raises FileNotFoundError: If the YAML file does not exist.
    """
    logger = setup_logger("ConfigLoader")
    storage = InMemoryStorage()

    # Register all entity handlers
    handlers = {
        'tasks': make_tasks_handlers(storage, logger),
        'docs': make_docs_handlers(storage, logger),
        'events': make_events_handlers(storage, logger),
        'telegram': make_telegram_handlers(logger),
    }

    if not os.path.exists(yaml_path):
        logger.critical(f"YAML config not found: {yaml_path}")
        raise FileNotFoundError(f"Config file {yaml_path} is missing")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for route in config.get('routes', []):
        path = route['path']
        method = route['method']
        entity = route['entity']
        action = route['action']

        if entity not in handlers or action not in handlers[entity]:
            logger.error(f"Unknown handler: {entity}.{action}")
            continue

        view_func = handlers[entity][action]

        # Wrap functions that require 'id' parameter
        if '<int:id>' in path or '<id>' in path:
            def make_wrapped(func, action_name=action):
                def wrapped(id):
                    return func(id)
                # Ensure unique function name for Flask
                wrapped.__name__ = f"{entity}_{action_name}_id_{id(wrapped)}"
                return wrapped
            view_func = make_wrapped(view_func)

        # Create unique endpoint name
        clean_path = path.replace('/', '_').replace('<', '').replace('>', '').strip('_')
        endpoint = f"{entity}_{action}_{clean_path}"
        app.add_url_rule(path, endpoint=endpoint, view_func=view_func, methods=[method])
        logger.info(f"Registered route: {method} {path} → {entity}.{action}")