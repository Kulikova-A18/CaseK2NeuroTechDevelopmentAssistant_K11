"""
Global variables for the modules.
Used to avoid circular imports.
"""

# These will be initialized in app.py
config_manager = None
users_manager = None
tasks_manager = None
events_manager = None
docs_manager = None
cache_manager = None
auth_manager = None
socketio = None