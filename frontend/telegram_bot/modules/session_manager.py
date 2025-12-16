"""
User session management.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class UserSession:
    """Class for storing user session data."""
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions = {}  # user_id -> session_data
    
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
        self.sessions[user_id] = session_data
    
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
        if 'access_token' in session:
            token = session['access_token']
        elif 'session_token' in session:
            token = session['session_token']
        elif 'token' in session:
            token = session['token']
        
        # Check in user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if 'access_token' in user_info:
                token = user_info['access_token']
            elif 'session_token' in user_info:
                token = user_info['session_token']
            elif 'token' in user_info:
                token = user_info['token']
        
        # Check in data inside user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if 'data' in user_info and isinstance(user_info['data'], dict):
                data = user_info['data']
                if 'access_token' in data:
                    token = data['access_token']
                elif 'session_token' in data:
                    token = data['session_token']
                elif 'token' in data:
                    token = data['token']
        
        if token:
            logger.debug(f"Token found for user {user_id}: {token[:10]}...")
        else:
            logger.warning(f"Token not found for user {user_id}. Available keys: {list(session.keys())}")
            if 'user_info' in session:
                logger.warning(f"User info keys: {list(session['user_info'].keys())}")
        
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
        
        return None
    
    def clear_session(self, user_id: int):
        """
        Clear user session.
        
        @param user_id: Telegram user ID
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Session cleared for user {user_id}")


# Create global instance
user_sessions = UserSession()