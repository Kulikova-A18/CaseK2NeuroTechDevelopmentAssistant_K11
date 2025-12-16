"""
WebSocket handlers for real-time communication.
Manages connections, subscriptions, and events.
"""

import logging
from datetime import datetime

from flask_socketio import emit, join_room

from modules.constants import SystemConstants


class WebSocketHandler:
    """
    Handles WebSocket connections and events.
    
    @param socketio: SocketIO instance
    @param auth_manager: Authentication manager instance
    """
    
    def __init__(self, socketio, auth_manager):
        self.socketio = socketio
        self.auth_manager = auth_manager
        
        # Register event handlers
        self.socketio.on_event('connect', self.handle_connect)
        self.socketio.on_event('subscribe', self.handle_subscribe)
        self.socketio.on_event('disconnect', self.handle_disconnect)
    
    def handle_connect(self):
        """
        WebSocket connection handler.
        Validates token and establishes connection.
        """
        from flask import request
        
        token = request.args.get('token')
        
        if not token:
            logging.warning("WebSocket connection without token")
            emit('error', {'message': 'Token required. Add ?token=YOUR_TOKEN to connection URL'})
            return False
        
        logging.debug(f"WebSocket connection with token: {token[:20]}...")
        
        # Validate token
        valid, user_info = self.auth_manager.validate_token(token, 'access')
        
        if not valid:
            logging.warning(f"Invalid WebSocket token: {token[:20]}...")
            emit('error', {'message': user_info.get('error', 'Invalid token')})
            
            # Send event about re-authentication needed
            if 'expired' in user_info.get('error', '').lower():
                emit(SystemConstants.WS_EVENTS['SESSION_EXPIRED'], {
                    'message': 'Session expired. Please re-authenticate.',
                    'timestamp': datetime.now().isoformat()
                })
            
            return False
        
        # Save connection information
        request.user_info = user_info
        logging.info(f"WebSocket connection: {user_info['telegram_username']}")
        
        emit('connected', {
            'message': 'WebSocket connected',
            'user': user_info['telegram_username'],
            'timestamp': datetime.now().isoformat()
        })
    
    def handle_subscribe(self, data):
        """
        Handler for WebSocket channel subscriptions.
        
        @param data: JSON with channels - list of channels to subscribe to
        """
        from flask import request
        
        if not hasattr(request, 'user_info'):
            logging.warning("WebSocket subscription without authentication")
            emit('error', {'message': 'Not authenticated'})
            return
        
        channels = data.get('channels', [])
        user_telegram = request.user_info['telegram_username']
        
        logging.info(f"User {user_telegram} subscribing to channels: {channels}")
        
        for channel in channels:
            join_room(channel)
            logging.debug(f"User {user_telegram} subscribed to channel {channel}")
        
        emit('subscribed', {
            'channels': channels,
            'message': 'Subscription successful'
        })
    
    def handle_disconnect(self):
        """WebSocket disconnect handler."""
        from flask import request
        
        if hasattr(request, 'user_info'):
            logging.info(f"WebSocket disconnect: {request.user_info['telegram_username']}")
            emit(SystemConstants.WS_EVENTS['USER_OFFLINE'], {
                'user': request.user_info['telegram_username'],
                'timestamp': datetime.now().isoformat()
            })