"""
Users API endpoints.
Handles user management operations.
"""

import logging
from flask import request

from modules.decorators import generate_response
from modules.models import UserCreate


class UsersAPI:
    """
    Users API endpoints.
    
    @param users_manager: CSV data manager for users
    @param auth_manager: Authentication manager instance
    @param config_manager: Configuration manager instance
    """
    
    def __init__(self, users_manager, auth_manager, config_manager):
        self.users_manager = users_manager
        self.auth_manager = auth_manager
        self.config_manager = config_manager
    
    def create_user_endpoint(self):
        """
        Endpoint for creating new user.
        Requires can_manage_users permission.
        
        Body: JSON with user data (UserCreate model)
        
        @return: JSON with created user
        """
        user_data = request.validated_data
        user_info = request.user_info
        
        logging.info(f"Create user request from: {user_info['telegram_username']}")
        logging.debug(f"New user data: {user_data.model_dump()}")
        
        # Check if user already exists
        existing_user = self.users_manager.find_one(
            telegram_username=user_data.telegram_username
        )
        if existing_user:
            logging.warning(f"User already exists: {user_data.telegram_username}")
            return generate_response(
                {'error': f'User {user_data.telegram_username} already exists'},
                status='error',
                status_code=400,
                config_manager=self.config_manager
            )
        
        # Prepare user data for saving to CSV
        user_dict = user_data.model_dump(exclude_unset=True)
        user_dict['is_active'] = str(user_dict['is_active'])
        
        # Create user
        try:
            created_user = self.users_manager.insert(user_dict)
            
            logging.info(f"User {user_data.telegram_username} created by {user_info['telegram_username']}")
            
            return generate_response({
                'user': created_user,
                'message': 'User created successfully'
            }, status_code=201, config_manager=self.config_manager)
        
        except Exception as e:
            logging.error(f"Error creating user: {e}")
            return generate_response(
                {'error': str(e)},
                status='error',
                status_code=500,
                config_manager=self.config_manager
            )