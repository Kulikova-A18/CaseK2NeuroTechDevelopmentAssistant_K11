"""
Authentication API endpoints.
Handles user login, token refresh, and logout.
"""

import logging
from flask import request, session, jsonify

from modules.decorators import generate_response
from modules.models import AuthRequest, RefreshTokenRequest


class AuthAPI:
    """
    Authentication API endpoints.
    
    @param auth_manager: Authentication manager instance
    @param config_manager: Configuration manager instance
    """
    
    def __init__(self, auth_manager, config_manager):
        self.auth_manager = auth_manager
        self.config_manager = config_manager
    
    def telegram_auth_endpoint(self):
        """
        Endpoint for Telegram authentication.
        Expects JSON with telegram_username and optional full_name.
        
        @return: JSON with token and user information
        """
        auth_data = request.validated_data
        
        logging.info(f"Authentication request from user: {auth_data.telegram_username}")
        
        # Authenticate user
        authenticated, result = self.auth_manager.authenticate_user(
            auth_data.telegram_username,
            auth_data.full_name
        )
        
        if not authenticated:
            logging.warning(f"Authentication failed for user: {auth_data.telegram_username}")
            return generate_response(
                result,
                status='error',
                status_code=401,
                config_manager=self.config_manager
            )
        
        # Save user_info to Flask session
        session['user_info'] = {
            'telegram_username': result['user'].get('telegram_username'),
            'role': result['user'].get('role', 'member'),
            'permissions': result.get('permissions', {})
        }
        
        # Set session lifetime
        session.permanent = True
        
        # Form response
        response_data = {
            'authenticated': True,
            'user': result['user'],
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'permissions': result['permissions'],
            'expires_in': result['expires_in']
        }
        
        logging.info(f"User {auth_data.telegram_username} authenticated successfully")
        return generate_response(response_data, status_code=200, config_manager=self.config_manager)
    
    def refresh_token_endpoint(self):
        """
        Endpoint for refreshing access token using refresh token.
        
        @return: JSON with new access token
        """
        refresh_data = request.validated_data
        
        logging.info(f"Token refresh request")
        
        # Refresh token
        success, result = self.auth_manager.refresh_access_token(refresh_data.refresh_token)
        
        if not success:
            logging.warning(f"Failed to refresh token: {result.get('error')}")
            return generate_response(
                result,
                status='error',
                status_code=401,
                config_manager=self.config_manager
            )
        
        # Update user_info in Flask session
        if 'user_info' in session:
            session['user_info']['telegram_username'] = result['user'].get('telegram_username')
            session['user_info']['role'] = result['user'].get('role', 'member')
            session['user_info']['permissions'] = result.get('permissions', {})
        
        # Form response
        response_data = {
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'expires_in': result['expires_in'],
            'user': result['user'],
            'permissions': result.get('permissions', {})
        }
        
        logging.info(f"Token refreshed successfully for user: {result['user'].get('telegram_username')}")
        return generate_response(response_data, status_code=200, config_manager=self.config_manager)
    
    def logout_endpoint(self):
        """
        Endpoint for user logout.
        
        @return: JSON with logout result
        """
        user_info = request.user_info
        telegram_username = user_info['telegram_username']
        
        logging.info(f"Logout request from user: {telegram_username}")
        
        # Logout user
        self.auth_manager.logout(telegram_username)
        
        # Remove Flask session
        session.pop('user_info', None)
        
        logging.info(f"User {telegram_username} logged out")
        return generate_response({
            'message': 'Successfully logged out',
            'logged_out': True
        }, config_manager=self.config_manager)