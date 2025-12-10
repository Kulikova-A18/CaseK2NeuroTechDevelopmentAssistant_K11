# handlers/telegram_notify.py
"""
Handler module for the 'telegram_notify' route.
This handler simulates sending a notification message to a specified Telegram chat.
In a real deployment, it would integrate with the Telegram Bot API.
Currently, it logs a mock notification for demonstration and testing purposes.
"""

from logger import get_logger
import logging

# Initialize a dedicated logger for this handler to record notification events and errors.
logger = get_logger("telegram_notify")


def _notify_core(chat_id, message):
    """
    Internal function that performs the actual notification delivery.

    In the current implementation, this is a **mock** that logs the intended
    notification instead of calling the Telegram Bot API. In a production system,
    this function should be replaced or extended to use `requests.post()` to
    `https://api.telegram.org/bot<TOKEN>/sendMessage` with appropriate payload.

    :param chat_id: (str or int) The Telegram chat ID to which the message should be sent.
                    This can be a user ID, group ID, or channel username (with '@').
    :param message: (str) The text content of the message to send.
    :return: None
    :raises Exception: Any exception that may occur during actual API communication
                       (not raised in mock mode, but should be handled in production).
    """
    # Mock implementation: log the notification instead of sending it
    logging.info(f"[MOCK NOTIFICATION] To {chat_id}: {message}")


def handle_request(data):
    """
    Handle an HTTP request to send a Telegram notification.

    This function validates the incoming request data, dispatches the notification
    via `_notify_core`, and returns an appropriate HTTP response. It follows the standard
    handler interface expected by the application's routing system.

    :param  (dict) A dictionary containing:
                 - `"chat_id"` (str or int): Identifier of the target Telegram chat.
                 - `"message"` (str): The text message to be delivered.
    :return: (tuple) A tuple containing:
             - (dict): A JSON-serializable response object:
                       - On success: `{"status": "notification dispatched"}`
                       - On failure: `{"error": "..."}` with a descriptive message.
             - (int): HTTP status code:
                       - 200 OK (success)
                       - 400 Bad Request (missing or invalid input)
                       - 500 Internal Server Error (unexpected exception during sending)
    """
    try:
        # Extract required parameters from the input data
        chat_id = data.get("chat_id")
        message = data.get("message")

        # Validate presence of both fields
        if not chat_id or not message:
            return {"error": "Both 'chat_id' and 'message' are required"}, 400

        # Dispatch the notification
        _notify_core(chat_id, message)

        # Log successful dispatch (for audit and debugging)
        logger.info(f"Notification sent to chat {chat_id}")

        return {"status": "notification dispatched"}, 200

    except Exception as e:
        # Log full exception details internally, but do not expose them to the client
        logger.error(f"Notify error: {e}", exc_info=True)
        return {"error": "Failed to send notification"}, 500