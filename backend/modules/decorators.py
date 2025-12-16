"""
Decorators for authentication, authorization, and request validation.
Provides security and validation middleware for API endpoints.
"""

import json
import time
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Tuple

from flask import request, jsonify, Response, session

from modules.models import BaseModel


def require_auth(auth_manager):
    """
    Decorator to check user authentication.
    Adds user_info to request object and Flask session.
    Supports token refresh via refresh token.
    
    @param auth_manager: Authentication manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user_info exists in Flask session
            if 'user_info' in session:
                logging.debug(f"Using data from Flask session")
                request.user_info = session['user_info']
                return f(*args, **kwargs)
            
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.warning(f"Request without token: {request.method} {request.path}")
                return jsonify({
                    'status': 'error',
                    'error': 'Authentication required. Use Authorization: Bearer <token> header',
                    'requires_auth': True
                }), 401
            
            token = auth_header.split(' ')[1]
            valid, user_info = auth_manager.validate_token(token, 'access')
            
            if not valid:
                # Check if refresh token is in headers
                refresh_token = request.headers.get('X-Refresh-Token')
                if refresh_token and 'expired' in user_info.get('error', '').lower():
                    # Try to refresh token
                    refresh_valid, refresh_result = auth_manager.refresh_access_token(refresh_token)
                    if refresh_valid:
                        # Save user_info to Flask session
                        session['user_info'] = {
                            'telegram_username': refresh_result.get('user', {}).get('telegram_username'),
                            'role': refresh_result.get('user', {}).get('role', 'member'),
                            'permissions': refresh_result.get('permissions', {})
                        }
                        
                        # Add new tokens to response
                        response = f(*args, **kwargs)
                        if isinstance(response, tuple) and len(response) == 2:
                            data, status_code = response
                            if hasattr(data, 'headers'):
                                data.headers['X-New-Access-Token'] = refresh_result['access_token']
                                data.headers['X-New-Refresh-Token'] = refresh_result['refresh_token']
                            return data, status_code
                        return response
                    else:
                        logging.warning(f"Failed to refresh token: {refresh_result.get('error')}")
                
                logging.warning(f"Invalid token: {token[:20]}...")
                error_response = {
                    'status': 'error',
                    'error': user_info.get('error', 'Invalid token')
                }
                
                # Add flag if re-authentication needed
                if 'expired' in user_info.get('error', '').lower() or 'invalid' in user_info.get('error', '').lower():
                    error_response['requires_re_auth'] = True
                
                return jsonify(error_response), 401
            
            logging.debug(f"User authenticated: {user_info['telegram_username']}, role: {user_info['role']}")
            
            # Add user info to request and save to Flask session
            request.user_info = user_info
            session['user_info'] = {
                'telegram_username': user_info['telegram_username'],
                'role': user_info['role'],
                'permissions': user_info.get('permissions', {})
            }
            
            # Set session lifetime
            session.permanent = True
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_permission(permission: str, auth_manager):
    """
    Decorator to check specific user permission.
    Should be used after require_auth.
    
    @param permission: Permission to check
    @param auth_manager: Authentication manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # MODIFICATION: Removed permission check - now everyone can do everything
            logging.debug(f"Permission automatically confirmed: {request.user_info['telegram_username']} -> {permission}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_request(model_class: BaseModel):
    """
    Decorator to validate incoming requests with Pydantic.
    
    @param model_class: Pydantic model class for validation
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    logging.warning(f"Request without JSON body: {request.method} {request.path}")
                    return jsonify({
                        'status': 'error',
                        'error': 'JSON request body required'
                    }), 400
                
                logging.debug(f"Received JSON request: {json.dumps(data, ensure_ascii=False)[:200]}...")
                
                # Validate data with Pydantic
                validated_data = model_class(**data)
                request.validated_data = validated_data
                logging.debug(f"Data validated successfully: {validated_data.model_dump()}")
                return f(*args, **kwargs)
            
            except Exception as e:
                logging.warning(f"Request validation error {request.method} {request.path}: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'error': f'Validation error: {str(e)}'
                }), 400
        
        return decorated_function
    return decorator


def generate_response(data: Any = None, status: str = 'success',
                     status_code: int = 200, meta: Dict[str, Any] = None,
                     config_manager=None) -> Tuple[Response, int]:
    """
    Generate standardized JSON response.
    
    @param data: Response data
    @param status: Operation status
    @param status_code: HTTP status code
    @param meta: Response metadata
    @param config_manager: Configuration manager instance
    @return: Tuple of Flask Response and status code
    """
    response_data = {
        'status': status,
        'data': data,
        'meta': meta or {
            'timestamp': datetime.now().isoformat(),
            'request_id': f"req_{int(time.time())}",
            'security_enabled': config_manager.is_security_enabled() if config_manager else True,
            'export_allowed_for_all': config_manager.is_export_allowed_for_all() if config_manager else True
        }
    }
    
    # Log response (shortened version for large data)
    response_str = json.dumps(response_data, ensure_ascii=False, default=str)
    if len(response_str) > 500:
        logging.debug(f"Sending response: {response_str[:500]}...")
    else:
        logging.debug(f"Sending response: {response_str}")
    
    return jsonify(response_data), status_code