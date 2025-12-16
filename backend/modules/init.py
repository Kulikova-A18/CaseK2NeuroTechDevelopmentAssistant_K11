"""
Modules package for task management system.
"""

from modules.constants import SystemConstants
from modules.models import *
from modules.config_manager import ConfigManager
from modules.csv_manager import CSVDataManager
from modules.cache_manager import CacheManager
from modules.auth_manager import AuthManager
from modules.decorators import *

# Initialize globals (will be set by app.py)
config_manager = None
users_manager = None
tasks_manager = None
events_manager = None
docs_manager = None
cache_manager = None
auth_manager = None