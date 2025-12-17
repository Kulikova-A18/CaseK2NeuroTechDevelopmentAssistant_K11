"""
User session management.
"""

import logging
from typing import Optional, Dict, Any, List
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class UserSession:
    """Class for storing user session data."""
    
    def __init__(self, storage_file: str = "user_sessions.json"):
        """
        Initialize session manager.
        
        @param storage_file: File to persist sessions
        """
        self.sessions = {}  # user_id -> session_data
        self.storage_file = storage_file
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    self.sessions = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(self.sessions)} sessions from {self.storage_file}")
            else:
                logger.info(f"No existing session file found at {self.storage_file}")
        except Exception as e:
            logger.error(f"Error loading sessions from {self.storage_file}: {e}")
            self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.sessions)} sessions to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving sessions to {self.storage_file}: {e}")
    
    def get_session(self, user_id: int) -> Dict[str, Any]:
        """
        Get user session data.
        
        @param user_id: Telegram user ID
        @return: Session data dictionary
        """
        return self.sessions.get(user_id, {})
    
    def set_session(self, user_id: int, session_data: Dict[str, Any]):
        """
        Set user session data.
        
        @param user_id: Telegram user ID
        @param session_data: Session data to store
        """
        # Add timestamp if not present
        if 'last_updated' not in session_data:
            session_data['last_updated'] = datetime.now().isoformat()
        
        # Add user_id to session data
        session_data['user_id'] = user_id
        
        self.sessions[user_id] = session_data
        self._save_sessions()
        logger.debug(f"Session set for user {user_id}")
    
    def update_session(self, user_id: int, **kwargs):
        """
        Update specific fields in user session.
        
        @param user_id: Telegram user ID
        @param kwargs: Key-value pairs to update
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = {}
        
        for key, value in kwargs.items():
            self.sessions[user_id][key] = value
        
        self.sessions[user_id]['last_updated'] = datetime.now().isoformat()
        self._save_sessions()
        logger.debug(f"Session updated for user {user_id}: {list(kwargs.keys())}")
    
    def get_token(self, user_id: int) -> Optional[str]:
        """
        Get user authentication token from session.
        
        @param user_id: Telegram user ID
        @return: Authentication token or None
        """
        session = self.get_session(user_id)
        if not session:
            logger.debug(f"Session not found for user {user_id}")
            return None
        
        # Look for token in different possible locations
        token = None
        
        # Check directly in session
        token_keys = ['access_token', 'session_token', 'token', 'auth_token', 'jwt_token']
        for key in token_keys:
            if key in session:
                token = session[key]
                break
        
        # Check in user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if isinstance(user_info, dict):
                for key in token_keys:
                    if key in user_info:
                        token = user_info[key]
                        break
        
        # Check in data inside user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if isinstance(user_info, dict) and 'data' in user_info:
                data = user_info['data']
                if isinstance(data, dict):
                    for key in token_keys:
                        if key in data:
                            token = data[key]
                            break
        
        if token:
            logger.debug(f"Token found for user {user_id}")
        else:
            logger.debug(f"Token not found for user {user_id}")
        
        return token
    
    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user information from session.
        
        @param user_id: Telegram user ID
        @return: User info dictionary or None
        """
        session = self.get_session(user_id)
        if not session:
            return None
        
        # Return user_info from different possible locations
        if 'user_info' in session:
            return session['user_info']
        elif 'user' in session:
            return {'user': session['user']}
        elif 'username' in session or 'first_name' in session:
            # Return basic user info from session
            user_info = {}
            if 'username' in session:
                user_info['username'] = session['username']
            if 'first_name' in session:
                user_info['first_name'] = session['first_name']
            if 'last_name' in session:
                user_info['last_name'] = session['last_name']
            return user_info
        
        return None
    
    def clear_session(self, user_id: int):
        """
        Clear user session.
        
        @param user_id: Telegram user ID
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            self._save_sessions()
            logger.info(f"Session cleared for user {user_id}")
    
    def get_all_users(self) -> List[int]:
        """
        Get list of all user IDs that have active sessions.
        
        @return: List of user IDs
        """
        return list(self.sessions.keys())
    
    def get_all_sessions(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all sessions data.
        
        @return: Copy of all sessions
        """
        return self.sessions.copy()
    
    def get_user_count(self) -> int:
        """
        Get total number of users with active sessions.
        
        @return: Count of users
        """
        return len(self.sessions)
    
    def is_user_active(self, user_id: int) -> bool:
        """
        Check if user has an active session.
        
        @param user_id: Telegram user ID
        @return: True if user has active session
        """
        return user_id in self.sessions
    
    def add_user_from_message(self, user_id: int, username: str = None, 
                              first_name: str = None, last_name: str = None):
        """
        Add or update user from Telegram message.
        
        @param user_id: Telegram user ID
        @param username: Telegram username
        @param first_name: User's first name
        @param last_name: User's last name
        """
        current_session = self.get_session(user_id)
        
        if not current_session:
            current_session = {}
        
        # Update user info
        if username:
            current_session['username'] = username
        if first_name:
            current_session['first_name'] = first_name
        if last_name:
            current_session['last_name'] = last_name
        
        # Add timestamps
        current_session['last_seen'] = datetime.now().isoformat()
        if 'first_seen' not in current_session:
            current_session['first_seen'] = datetime.now().isoformat()
        
        self.set_session(user_id, current_session)
        logger.info(f"User {user_id} (@{username}) added/updated in sessions")
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """
        Remove sessions older than specified days.
        
        @param days_old: Remove sessions older than this many days
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        user_ids_to_remove = []
        
        for user_id, session in self.sessions.items():
            last_seen_str = session.get('last_seen') or session.get('last_updated')
            if last_seen_str:
                try:
                    last_seen = datetime.fromisoformat(last_seen_str)
                    if last_seen < cutoff_date:
                        user_ids_to_remove.append(user_id)
                except ValueError:
                    # If date parsing fails, keep the session
                    continue
        
        for user_id in user_ids_to_remove:
            del self.sessions[user_id]
            removed_count += 1
        
        if removed_count > 0:
            self._save_sessions()
            logger.info(f"Cleaned up {removed_count} old sessions (older than {days_old} days)")
        
        return removed_count
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about sessions.
        
        @return: Dictionary with session statistics
        """
        total_users = len(self.sessions)
        
        # Count users with tokens
        users_with_token = 0
        for user_id in self.sessions:
            if self.get_token(user_id):
                users_with_token += 1
        
        # Get newest and oldest sessions
        newest_session = None
        oldest_session = None
        
        for session in self.sessions.values():
            last_seen = session.get('last_seen')
            if last_seen:
                if not newest_session or last_seen > newest_session:
                    newest_session = last_seen
                if not oldest_session or last_seen < oldest_session:
                    oldest_session = last_seen
        
        return {
            'total_users': total_users,
            'users_with_token': users_with_token,
            'newest_session': newest_session,
            'oldest_session': oldest_session,
            'sessions_file': self.storage_file
        }


# Create global instance
user_sessions = UserSession()