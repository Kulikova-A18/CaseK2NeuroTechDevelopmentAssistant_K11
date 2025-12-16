"""
Authentication and authorization manager.
Handles user authentication, token validation, and permission checking.
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from modules.constants import SystemConstants
from modules.config_manager import ConfigManager


class AuthManager:
    """
    Manager for authentication, authorization, and user permissions.
    
    @param config_manager: Configuration manager instance
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.jwt_secret = os.environ.get('JWT_SECRET', 'your-secret-key-change-this')
        self.session_timeout = config_manager.get('security.session_timeout_hours', 24)
        self.refresh_token_days = config_manager.get('security.refresh_token_days', 7)
        self.security_enabled = config_manager.is_security_enabled()
        self.export_allowed_for_all = config_manager.is_export_allowed_for_all()
        
        # Store managers that will be injected later
        self.users_manager = None
        self.cache_manager = None
        
        # Roles and their permissions (from config or default)
        self.roles_permissions = self._load_roles_permissions()
    
    def set_managers(self, users_manager, cache_manager):
        """
        Set the managers after initialization to avoid circular imports.
        
        @param users_manager: CSV data manager for users
        @param cache_manager: Cache manager instance
        """
        self.users_manager = users_manager
        self.cache_manager = cache_manager
    
    def _load_roles_permissions(self) -> Dict[str, Dict[str, Any]]:
        """
        Load permissions for roles.
        If security is disabled, all users get admin permissions.
        
        @return: Permissions for each role
        """
        if not self.security_enabled:
            # If security is disabled, everyone has admin permissions
            admin_permissions = {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': True,
                'llm_daily_limit': 999999  # Practically unlimited
            }
            return {role: admin_permissions.copy() for role in SystemConstants.ROLES}
        
        # Default permissions for various roles
        permissions = {
            'admin': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': True,
                'llm_daily_limit': 50
            },
            'manager': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': False,
                'llm_daily_limit': 20
            },
            'member': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': False,
                'can_export': self.export_allowed_for_all,
                'can_use_llm': True,
                'can_manage_users': False,
                'llm_daily_limit': 5
            },
            'viewer': {
                'can_create_tasks': False,
                'can_edit_tasks': False,
                'can_delete_tasks': False,
                'can_export': self.export_allowed_for_all,
                'can_use_llm': False,
                'can_manage_users': False,
                'llm_daily_limit': 0
            }
        }
        
        return permissions
    
    def authenticate_user(self, telegram_username: str, full_name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user via Telegram.
        If user not found and security is disabled, creates new user.
        
        @param telegram_username: Telegram username
        @param full_name: User's full name (optional)
        @return: Tuple (authentication success, user data or error)
        """
        try:
            logging.info(f"Authentication attempt for user: {telegram_username}")
            
            # Check if managers are set
            if not self.users_manager or not self.cache_manager:
                logging.error("Managers not initialized in AuthManager")
                return False, {'error': 'Authentication system not ready'}
            
            # Search for user
            user = self.users_manager.find_one(telegram_username=telegram_username)
            
            if user:
                logging.info(f"User {telegram_username} found in database")
                
                # Check activity
                if user.get('is_active', 'False') != 'True':
                    logging.warning(f"User {telegram_username} is inactive")
                    return False, {'error': 'User is inactive'}
                
                # Update last_login
                self.users_manager.update(
                    {'telegram_username': telegram_username},
                    {'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                )
                
                # Get permissions
                role = user.get('role', 'member')
                permissions = self.roles_permissions.get(role, {}).copy()
                
                # Generate access token
                token_payload = {
                    'telegram_username': telegram_username,
                    'role': role,
                    'type': 'access',
                    'exp': datetime.utcnow() + timedelta(hours=self.session_timeout)
                }
                
                # Generate refresh token
                refresh_payload = {
                    'telegram_username': telegram_username,
                    'type': 'refresh',
                    'exp': datetime.utcnow() + timedelta(days=self.refresh_token_days)
                }
                
                access_token = jwt.encode(token_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)
                refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)
                
                # Save session to cache
                session_key = f"session:{telegram_username}"
                self.cache_manager.set(session_key, {
                    'user': user,
                    'permissions': permissions,
                    'refresh_token': refresh_token,
                    'last_activity': datetime.now().isoformat()
                }, ttl=self.session_timeout * 3600)
                
                # Save refresh token
                refresh_key = f"refresh:{telegram_username}"
                self.cache_manager.set(refresh_key, {
                    'refresh_token': refresh_token,
                    'created_at': datetime.now().isoformat(),
                    'user': user
                }, ttl=self.refresh_token_days * 24 * 3600)
                
                logging.info(f"User {telegram_username} authenticated successfully, role: {role}")
                return True, {
                    'user': user,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'permissions': permissions,
                    'expires_in': self.session_timeout * 3600
                }
            
            # User not found
            logging.info(f"User {telegram_username} not found in database")
            
            # If security disabled or auto-registration enabled, create new user
            new_user = {
                'telegram_username': telegram_username,
                'full_name': full_name or telegram_username.replace('@', ''),
                'role': 'member',
                'is_active': 'True'
            }
            
            logging.info(f"Creating new user: {telegram_username}")
            user = self.users_manager.insert(new_user)
            
            # Re-authenticate new user
            return self.authenticate_user(telegram_username, full_name)
        
        except Exception as e:
            logging.error(f"Authentication error for user {telegram_username}: {e}")
            return False, {'error': str(e)}
    
    def validate_token(self, token: str, token_type: str = 'access') -> Tuple[bool, Dict[str, Any]]:
        """
        Validate JWT token.
        
        @param token: JWT token
        @param token_type: Token type (access or refresh)
        @return: Tuple (token valid, user data or error)
        """
        try:
            logging.debug(f"Validating {token_type} token: {token[:20]}...")
            
            payload = jwt.decode(token, self.jwt_secret, algorithms=[SystemConstants.JWT_ALGORITHM])
            
            # Check token type
            if payload.get('type') != token_type:
                logging.warning(f"Wrong token type: expected {token_type}, got {payload.get('type')}")
                return False, {'error': f'Wrong token type. Expected {token_type} token.'}
            
            telegram_username = payload.get('telegram_username')
            
            if token_type == 'access':
                # Check if cache manager is set
                if not self.cache_manager:
                    logging.error("Cache manager not initialized")
                    return False, {'error': 'Authentication system not ready'}
                
                # Check session in cache
                session_key = f"session:{telegram_username}"
                session_data = self.cache_manager.get(session_key)
                
                if not session_data:
                    logging.warning(f"Session expired for user: {telegram_username}")
                    return False, {'error': 'Session expired. Please refresh token.'}
                
                # Check refresh token match
                refresh_key = f"refresh:{telegram_username}"
                refresh_data = self.cache_manager.get(refresh_key)
                
                if not refresh_data or session_data.get('refresh_token') != refresh_data.get('refresh_token'):
                    logging.warning(f"Refresh token mismatch or expired: {telegram_username}")
                    return False, {'error': 'Invalid session. Please re-authenticate.'}
                
                # Update activity time
                session_data['last_activity'] = datetime.now().isoformat()
                self.cache_manager.set(session_key, session_data, ttl=self.session_timeout * 3600)
                
                logging.debug(f"Access token valid for user: {telegram_username}")
                return True, {
                    'telegram_username': telegram_username,
                    'role': payload.get('role'),
                    'user': session_data.get('user'),
                    'permissions': session_data.get('permissions', {})
                }
            else:
                # Validate refresh token
                if not self.cache_manager:
                    logging.error("Cache manager not initialized")
                    return False, {'error': 'Authentication system not ready'}
                
                refresh_key = f"refresh:{telegram_username}"
                refresh_data = self.cache_manager.get(refresh_key)
                
                if not refresh_data or refresh_data.get('refresh_token') != token:
                    logging.warning(f"Refresh token not found or mismatch: {telegram_username}")
                    return False, {'error': 'Invalid refresh token'}
                
                logging.debug(f"Refresh token valid for user: {telegram_username}")
                return True, {
                    'telegram_username': telegram_username,
                    'user': refresh_data.get('user')
                }
        
        except jwt.ExpiredSignatureError:
            if token_type == 'access':
                logging.warning("Access token expired")
                return False, {'error': 'Access token expired. Use refresh token to get new one.'}
            else:
                logging.warning("Refresh token expired")
                return False, {'error': 'Refresh token expired. Please re-authenticate.'}
        except jwt.InvalidTokenError as e:
            logging.warning(f"Invalid token: {str(e)}")
            return False, {'error': f'Invalid token: {str(e)}'}
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        @param refresh_token: Refresh token
        @return: Tuple (success, new tokens or error)
        """
        try:
            # Validate refresh token
            valid, refresh_info = self.validate_token(refresh_token, 'refresh')
            
            if not valid:
                return False, refresh_info
            
            telegram_username = refresh_info['telegram_username']
            user = refresh_info['user']
            
            # Get user role
            role = user.get('role', 'member')
            permissions = self.roles_permissions.get(role, {}).copy()
            
            # Generate new access token
            token_payload = {
                'telegram_username': telegram_username,
                'role': role,
                'type': 'access',
                'exp': datetime.utcnow() + timedelta(hours=self.session_timeout)
            }
            
            access_token = jwt.encode(token_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)
            
            # Update session in cache
            session_key = f"session:{telegram_username}"
            self.cache_manager.set(session_key, {
                'user': user,
                'permissions': permissions,
                'refresh_token': refresh_token,
                'last_activity': datetime.now().isoformat()
            }, ttl=self.session_timeout * 3600)
            
            logging.info(f"Access token refreshed for user: {telegram_username}")
            return True, {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': self.session_timeout * 3600,
                'user': user,
                'permissions': permissions
            }
        
        except Exception as e:
            logging.error(f"Token refresh error: {e}")
            return False, {'error': str(e)}
    
    def check_permission(self, user_info: Dict[str, Any], permission: str) -> bool:
        """
        Check user permission.
        
        @param user_info: User information
        @param permission: Permission to check
        @return: True if user has permission
        """
        # MODIFICATION: Removed permission check - now everyone can do everything
        logging.debug(f"Security simplified, access granted: {permission}")
        return True
    
    def get_user_llm_quota(self, telegram_username: str) -> Dict[str, Any]:
        """
        Get user's LLM request quota.
        
        @param telegram_username: Telegram username
        @return: Quota information
        """
        if not self.cache_manager or not self.users_manager:
            return {
                'used': 0,
                'limit': 50,
                'reset_at': (datetime.now() + timedelta(days=1)).isoformat()
            }
        
        cache_key = f"llm_quota:{telegram_username}:{datetime.now().strftime('%Y-%m-%d')}"
        quota_data = self.cache_manager.get(cache_key) or {
            'used': 0,
            'limit': 0,
            'reset_at': (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        # Get limit from user role
        user = self.users_manager.find_one(telegram_username=telegram_username)
        role = user.get('role', 'member') if user else 'member'
        quota_data['limit'] = self.roles_permissions.get(role, {}).get('llm_daily_limit', 0)
        
        return quota_data
    
    def logout(self, telegram_username: str):
        """
        Log out user (delete session).
        
        @param telegram_username: Telegram username
        """
        if not self.cache_manager:
            return
        
        # Delete session
        session_key = f"session:{telegram_username}"
        self.cache_manager.delete(session_key)
        
        # Delete refresh token
        refresh_key = f"refresh:{telegram_username}"
        self.cache_manager.delete(refresh_key)
        
        logging.info(f"User {telegram_username} logged out")