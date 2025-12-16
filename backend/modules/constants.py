"""
System-wide constants and configuration parameters.
Contains all enums, statuses, roles, and file paths used throughout the system.
"""

from datetime import timedelta


class SystemConstants:
    """Class containing all system constants."""
    
    # User roles
    ROLES = ['admin', 'manager', 'member', 'viewer']
    
    # Task statuses
    TASK_STATUSES = ['todo', 'in_progress', 'done']
    
    # Task priorities
    TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent']
    
    # Document access levels
    DOC_ACCESS_LEVELS = ['public', 'team', 'private']
    
    # Time periods for analysis
    TIME_PERIODS = ['last_week', 'last_month', 'last_quarter', 'custom']
    
    # Metrics for LLM analysis
    LLM_METRICS = ['productivity', 'bottlenecks', 'team_performance', 'predictions']
    
    # Export formats
    EXPORT_FORMATS = ['csv', 'xlsx']
    
    # Data directory paths
    DATA_DIR = './data'
    CSV_PATHS = {
        'users': f'{DATA_DIR}/users.csv',
        'tasks': f'{DATA_DIR}/tasks.csv',
        'events': f'{DATA_DIR}/events.csv',
        'docs': f'{DATA_DIR}/docs.csv'
    }
    
    # Default values
    DEFAULT_SESSION_TIMEOUT_HOURS = 24
    DEFAULT_REFRESH_TOKEN_DAYS = 7
    DEFAULT_CACHE_TTL_SECONDS = 300
    DEFAULT_RATE_LIMIT_PER_MINUTE = 100
    DEFAULT_LLM_REQUESTS_PER_DAY = 50
    
    # JWT settings
    JWT_ALGORITHM = 'HS256'
    
    # WebSocket events
    WS_EVENTS = {
        'TASK_CREATED': 'task_created',
        'TASK_UPDATED': 'task_updated',
        'TASK_DELETED': 'task_deleted',
        'EVENT_CREATED': 'event_created',
        'USER_ONLINE': 'user_online',
        'USER_OFFLINE': 'user_offline',
        'SESSION_EXPIRED': 'session_expired'
    }
    
    # CSV schemas
    USERS_SCHEMA = {
        'telegram_username': {'required': True, 'type': 'string'},
        'full_name': {'required': True, 'type': 'string'},
        'role': {'required': True, 'type': 'string', 'default': 'member'},
        'is_active': {'required': True, 'type': 'boolean', 'default': 'True'},
        'registered_at': {'required': False, 'type': 'datetime'},
        'last_login': {'required': False, 'type': 'datetime'},
        'email': {'required': False, 'type': 'string'},
        'department': {'required': False, 'type': 'string'}
    }
    
    TASKS_SCHEMA = {
        'task_id': {'required': True, 'type': 'integer'},
        'title': {'required': True, 'type': 'string'},
        'description': {'required': False, 'type': 'string'},
        'status': {'required': True, 'type': 'string', 'default': 'todo'},
        'assignee': {'required': False, 'type': 'string'},
        'creator': {'required': True, 'type': 'string'},
        'created_at': {'required': False, 'type': 'datetime'},
        'updated_at': {'required': False, 'type': 'datetime'},
        'due_date': {'required': False, 'type': 'date'},
        'completed_at': {'required': False, 'type': 'datetime'},
        'priority': {'required': True, 'type': 'string', 'default': 'medium'},
        'tags': {'required': False, 'type': 'json'}
    }
    
    EVENTS_SCHEMA = {
        'event_id': {'required': True, 'type': 'integer'},
        'title': {'required': True, 'type': 'string'},
        'description': {'required': False, 'type': 'string'},
        'start_time': {'required': True, 'type': 'datetime'},
        'end_time': {'required': True, 'type': 'datetime'},
        'creator': {'required': True, 'type': 'string'},
        'participants': {'required': False, 'type': 'json'},
        'created_at': {'required': False, 'type': 'datetime'},
        'location': {'required': False, 'type': 'string'}
    }
    
    DOCS_SCHEMA = {
        'doc_id': {'required': True, 'type': 'integer'},
        'title': {'required': True, 'type': 'string'},
        'content': {'required': False, 'type': 'text'},
        'file_path': {'required': False, 'type': 'string'},
        'creator': {'required': True, 'type': 'string'},
        'created_at': {'required': False, 'type': 'datetime'},
        'updated_at': {'required': False, 'type': 'datetime'},
        'access_level': {'required': True, 'type': 'string', 'default': 'team'},
        'version': {'required': False, 'type': 'string'}
    }