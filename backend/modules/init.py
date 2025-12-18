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
from modules.file_hash_manager import *

from modules.agent_core.llm_core.agent_process import *
from modules.agent_core.llm_core.analytics import *
from modules.agent_core.llm_core.blockers import *
from modules.agent_core.llm_core.daily import *
from modules.agent_core.llm_core.digest import *
from modules.agent_core.llm_core.faq import *
from modules.agent_core.llm_core.prompts import *
from modules.agent_core.llm_core.schemas import *

# Initialize globals (will be set by app.py)
config_manager = None
users_manager = None
tasks_manager = None
events_manager = None
docs_manager = None
cache_manager = None
auth_manager = None
file_hash_manager = None