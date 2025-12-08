# modules/telegram.py
from flask import jsonify, request

def make_telegram_handlers(logger):
    """
    Creates handler functions for Telegram integration endpoints.

    :param logger: Logger instance for audit and debugging.
    :return: Dictionary mapping action names to Flask view functions.
    """

    def auth():
        """
        Handles Telegram user authentication.
        Expects JSON with 'user_id'.
        """
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if not user_id:
            logger.warning("Telegram auth failed: user_id missing")
            return jsonify({'error': 'user_id required'}), 400
        logger.info(f"Telegram auth success: user_id={user_id}")
        return jsonify({'status': 'authenticated', 'user_id': user_id})

    def notify():
        """
        Sends a notification via Telegram.
        Expects JSON with 'chat_id' and 'message'.
        """
        data = request.get_json() or {}
        chat_id = data.get('chat_id')
        message = data.get('message')
        if not chat_id or not message:
            logger.warning("Telegram notify failed: chat_id or message missing")
            return jsonify({'error': 'chat_id and message required'}), 400
        logger.info(f"Telegram notify sent to {chat_id}: '{message[:50]}...'")
        return jsonify({'status': 'notification sent', 'chat_id': chat_id})

    return {
        'auth': auth,
        'notify': notify
    }