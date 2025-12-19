"""
Configuration manager for the system.
Loads settings from YAML file and replaces environment variables.
"""

import os
import yaml
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any


class ConfigManager:
    """
    Manages system configuration.
    Loads settings from YAML file and replaces environment variables.
    
    @param config_path: Path to YAML configuration file
    """
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        @return: Dictionary with configuration
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Replace environment variables
            config = self._replace_env_vars(config)
            return config
        except FileNotFoundError:
            logging.error(f"Configuration file {self.config_path} not found")
            return self._get_default_config()
    
    def _replace_env_vars(self, config: Dict) -> Dict:
        """
        Replace strings like ${VAR} with environment variable values.
        
        @param config: Configuration with variables
        @return: Configuration with replaced variables
        """
        import re
        
        def replace(obj):
            if isinstance(obj, dict):
                return {k: replace(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace(item) for item in obj]
            elif isinstance(obj, str):
                # Find pattern ${VAR_NAME}
                match = re.search(r'\${(\w+)}', obj)
                if match:
                    env_var = match.group(1)
                    env_value = os.environ.get(env_var, '')
                    return obj.replace(f'${{{env_var}}}', env_value)
                return obj
            else:
                return obj
        
        return replace(config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        @return: Default configuration dictionary
        """
        return {
            'security': {
                'enabled': True,
                'validation_method': 'telegram_username',
                'session_timeout_hours': 24,
                'refresh_token_days': 7,
                'admin_only_endpoints': ['/api/users', '/api/system/*'],
                'rate_limiting': {
                    'requests_per_minute': 100,
                    'llm_requests_per_day': 50
                }
            },
            'logging': {
                'level': 'INFO',
                'file_path': './logs/task_system.log',
                'max_size_mb': 100,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'retention_days': 30
            },
            'performance': {
                'cache_enabled': True,
                'cache_ttl_seconds': 300,
                'csv_read_batch_size': 1000,
                'worker_processes': 4,
                'max_file_size_mb': 10
            },
            'telegram': {
                'bot_token': '',
                'webhook_url': 'https://api.example.com/webhook',
                'polling_interval': 2
            },
            'llm': {
                'enabled': True,
                'provider': 'openai',
                'api_key': '',
                'model': 'gpt-4-turbo-preview',
                'max_tokens': 2000,
                'cache_minutes': 60,
                'timeout_seconds': 60
            },
            'server': {
                'host': '0.0.0.0',
                'port': 5000,
                'ssl_enabled': False,
                'max_connections': 1000,
                'request_timeout': 30,
                'cors_origins': [
                    'https://kanban.example.com',
                    'http://backend:3000'
                ],
                'debug': False
            },
            'export': {
                'allow_all': True,  # Allow export to all users
                'csv_export_enabled': True,
                'max_export_records': 10000
            }
        }
    
    def _setup_logging(self):
        """Setup logging system based on configuration."""
        log_config = self.config.get('logging', {})
        
        # Create logs directory
        log_dir = os.path.dirname(log_config.get('file_path', './logs/app.log'))
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        
        # Formatter
        formatter = logging.Formatter(log_config.get('format'))
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_config.get('file_path'),
            maxBytes=log_config.get('max_size_mb', 100) * 1024 * 1024,
            backupCount=log_config.get('retention_days', 30)
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logging.info(f"Logging initialized. File: {log_config.get('file_path')}")
    
    def get(self, key: str, default=None) -> Any:
        """
        Get configuration value by key.
        
        @param key: Configuration key in format 'section.subsection'
        @param default: Default value if key not found
        @return: Configuration value
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def is_security_enabled(self) -> bool:
        """
        Check if security is enabled.
        
        @return: True if security is enabled
        """
        return self.get('security.enabled', True)
    
    def is_export_allowed_for_all(self) -> bool:
        """
        Check if export is allowed for all users.
        
        @return: True if export is allowed for all
        """
        return self.get('export.allow_all', True)