"""
Main server file for task management system.
Uses Flask for REST API, Pydantic for validation, and SocketIO for WebSocket.
"""

import os
import time
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from modules.config_manager import ConfigManager
from modules.csv_manager import CSVDataManager
from modules.cache_manager import CacheManager
from modules.auth_manager import AuthManager
from modules.websocket import WebSocketHandler
from modules.api.auth import AuthAPI
from modules.api.tasks import TasksAPI
from modules.api.users import UsersAPI
from modules.api.export import ExportAPI
from modules.api.llm import LLMAPI
from modules.constants import SystemConstants
from modules.models import AuthRequest, RefreshTokenRequest, TaskCreate, TaskUpdate, UserCreate, LLMAnalysisRequest
from modules.decorators import require_auth, require_permission, validate_request
from modules.utils import initialize_sample_data
from modules.file_hash_manager import *


# ============================================================================
# INITIALIZATION
# ============================================================================

# Setup logging
def setup_logging():
    """Setup application logging."""
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = RotatingFileHandler(
        f'{log_dir}/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

setup_logging()

# Initialize configuration manager
config_manager = ConfigManager()

# Initialize CSV data managers
users_manager = CSVDataManager(SystemConstants.CSV_PATHS['users'], SystemConstants.USERS_SCHEMA)
tasks_manager = CSVDataManager(SystemConstants.CSV_PATHS['tasks'], SystemConstants.TASKS_SCHEMA)
events_manager = CSVDataManager(SystemConstants.CSV_PATHS['events'], SystemConstants.EVENTS_SCHEMA)
docs_manager = CSVDataManager(SystemConstants.CSV_PATHS['docs'], SystemConstants.DOCS_SCHEMA)

# Initialize cache manager
cache_enabled = config_manager.get('performance.cache_enabled', True)
cache_ttl = config_manager.get('performance.cache_ttl_seconds', SystemConstants.DEFAULT_CACHE_TTL_SECONDS)
cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)

# Initialize authentication manager
auth_manager = AuthManager(config_manager)
# Inject managers into auth_manager
auth_manager.set_managers(users_manager, cache_manager)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-this')
CORS(app, origins=config_manager.get('server.cors_origins', ["*"]))

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize WebSocket handler
websocket_handler = WebSocketHandler(socketio, auth_manager)

# Initialize API handlers
auth_api = AuthAPI(auth_manager, config_manager)
tasks_api = TasksAPI(tasks_manager, users_manager, cache_manager, auth_manager, config_manager, socketio)
users_api = UsersAPI(users_manager, auth_manager, config_manager)
export_api = ExportAPI(tasks_manager, users_manager, cache_manager, config_manager)
llm_api = LLMAPI(auth_manager, config_manager, cache_manager)


# ============================================================================
# API ROUTES
# ============================================================================

# Authentication routes
@app.route('/api/telegram/auth', methods=['POST'])
@validate_request(AuthRequest)
def telegram_auth():
    return auth_api.telegram_auth_endpoint()

@app.route('/api/auth/refresh', methods=['POST'])
@validate_request(RefreshTokenRequest)
def refresh_token():
    return auth_api.refresh_token_endpoint()

@app.route('/api/auth/logout', methods=['POST'])
@require_auth(auth_manager)
def logout():
    return auth_api.logout_endpoint()

# Tasks routes
@app.route('/api/tasks', methods=['GET'])
@require_auth(auth_manager)
def get_tasks():
    return tasks_api.get_tasks_endpoint()

@app.route('/api/tasks', methods=['POST'])
@require_auth(auth_manager)
# @require_permission('can_create_tasks', auth_manager)
@validate_request(TaskCreate)
def create_task():
    return tasks_api.create_task_endpoint()

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@require_auth(auth_manager)
@validate_request(TaskUpdate)
def update_task(task_id):
    return tasks_api.update_task_endpoint(task_id)

# Users routes
@app.route('/api/users', methods=['POST'])
@require_permission('can_manage_users', auth_manager)
@validate_request(UserCreate)
def create_user():
    return users_api.create_user_endpoint()

# Export routes
@app.route('/api/export/tasks.csv', methods=['GET'])
def export_tasks_csv():
    return export_api.export_tasks_csv_endpoint()

# LLM routes
@app.route('/api/llm/analyze/tasks', methods=['POST'])
@require_permission('can_use_llm', auth_manager)
@validate_request(LLMAnalysisRequest)
def analyze_tasks_llm():
    return llm_api.analyze_tasks_llm_endpoint()

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'components': {
            'flask': 'running',
            'csv_storage': 'ok',
            'cache': 'enabled' if cache_manager.enabled else 'disabled',
            'llm': 'demo-mode',
            'security': 'enabled' if config_manager.is_security_enabled() else 'disabled',
            'export_for_all': config_manager.is_export_allowed_for_all()
        },
        'metrics': {
            'users_count': len(users_manager.read_all()),
            'tasks_count': len(tasks_manager.read_all()),
            'events_count': len(events_manager.read_all()),
            'docs_count': len(docs_manager.read_all()),
            'uptime_seconds': app_start_time if 'app_start_time' in globals() else 0
        },
        'config': {
            'security_enabled': config_manager.is_security_enabled(),
            'cache_enabled': cache_manager.enabled,
            'server_port': config_manager.get('server.port', 5000),
            'export_allowed_for_all': config_manager.is_export_allowed_for_all()
        }
    }
    return jsonify(health_status)

# Root endpoint
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Task Management System API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health',
            'auth': '/api/telegram/auth',
            'tasks': '/api/tasks',
            'export': '/api/export/tasks.csv',
            'llm': '/api/llm/analyze/tasks'
        }
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'error': 'Internal server error'
    }), 500


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == '__main__':
    # Record application start time
    app_start_time = int(time.time())
    
    # Create necessary directories
    os.makedirs(SystemConstants.DATA_DIR, exist_ok=True)
    os.makedirs('./logs', exist_ok=True)

    # delete on real product
    # Initialize sample data
    try:
        initialize_sample_data(tasks_manager, users_manager)
        logging.info("Sample data initialized successfully")
    except Exception as e:
        logging.warning(f"Could not initialize sample data: {e}")
    
    # Get server configuration
    server_config = config_manager.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', False)
    
    logging.info(f"Starting task management system server")
    logging.info(f"Address: http://{host}:{port}")
    logging.info(f"Debug mode: {debug}")
    logging.info(f"Security: {'enabled' if config_manager.is_security_enabled() else 'disabled'}")
    logging.info(f"Export for all users: {'allowed' if config_manager.is_export_allowed_for_all() else 'requires authentication'}")
    logging.info(f"Available endpoints:")
    logging.info(f"  - GET  / - API documentation")
    logging.info(f"  - GET  /api/health - System health check")
    logging.info(f"  - POST /api/telegram/auth - Telegram authentication")
    logging.info(f"  - POST /api/auth/refresh - Token refresh")
    logging.info(f"  - POST /api/auth/logout - Logout")
    logging.info(f"  - GET  /api/tasks - Get task list")
    logging.info(f"  - POST /api/tasks - Create task")
    logging.info(f"  - PUT  /api/tasks/<id> - Update task")
    logging.info(f"  - GET  /api/export/tasks.csv - Export tasks to CSV")
    logging.info(f"  - POST /api/llm/analyze/tasks - Task analysis (demo)")
    logging.info(f"  - POST /api/users - Create user")
    
    # Start server
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )
