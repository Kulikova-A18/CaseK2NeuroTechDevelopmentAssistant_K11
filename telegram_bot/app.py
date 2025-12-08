import requests
import time
import json
import logging
import random

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - INSERT YOUR TOKEN HERE
TOKEN = '8521671675:AAGHly...'
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'


def get_updates(offset=None):
    """Get updates from Telegram"""
    url = f'{BASE_URL}/getUpdates'
    # param: timeout - long polling timeout in seconds
    # param: offset - identifier of the first update to be returned
    params = {'timeout': 30, 'offset': offset} if offset else {'timeout': 30}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # Check for API errors
        if not data.get('ok'):
            logger.error(f"API Error: {data.get('description', 'Unknown error')}")
            return []

        return data.get('result', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return []


def send_message(chat_id, text, reply_markup=None):
    """Send message to user"""
    url = f'{BASE_URL}/sendMessage'
    # param: chat_id - unique identifier for the target chat
    # param: text - text of the message to be sent
    # param: parse_mode - mode for parsing entities in the message text
    # param: disable_web_page_preview - disable link previews
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }

    # param: reply_markup - additional interface options
    if reply_markup:
        data['reply_markup'] = reply_markup

    try:
        # param: timeout - request timeout in seconds
        response = requests.post(url, json=data, timeout=10)
        result = response.json()

        if not result.get('ok'):
            logger.error(f"Error sending message: {result.get('description')}")

        return result
    except requests.exceptions.Timeout:
        logger.error("Timeout while sending message")
        return None
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None


def get_keyboard():
    """Create custom keyboard with buttons"""
    keyboard = {
        'keyboard': [
            ['Say Hello', 'Information'],
            ['Help', 'Refresh']
        ],
        # param: resize_keyboard - resize keyboard to fit buttons
        'resize_keyboard': True,
        # param: one_time_keyboard - hide keyboard after use
        'one_time_keyboard': False
    }
    return json.dumps(keyboard)


def process_update(update):
    """Process single update from Telegram"""
    if 'message' not in update:
        return None

    message = update['message']
    chat_id = message['chat']['id']
    text = message.get('text', '').strip()

    # Get user information
    user = message.get('from', {})
    user_id = user.get('id')
    username = user.get('username', 'no username')
    first_name = user.get('first_name', 'User')

    # Log the message
    logger.info(f"Message from {username} ({user_id}): {text}")

    # Process commands and text
    if text.startswith('/'):
        command = text.split()[0].lower()

        if command == '/start':
            response = (
                f"Hello, <b>{first_name}!</b>\n\n"
                f"I am <b>K2NeuroAssist_bot</b>\n"
                f"Created to demonstrate Telegram bot functionality.\n\n"
                f"What I can do:\n"
                f"• Always say 'Hello'\n"
                f"• Respond to commands\n"
                f"• Show buttons for convenience\n\n"
                f"Use /help command for assistance."
            )
            keyboard = get_keyboard()

        elif command == '/help':
            response = (
                "<b>Command Help:</b>\n\n"
                "<b>Main commands:</b>\n"
                "/start - Start working with the bot\n"
                "/help - This help message\n"
                "/hello - Personal greeting\n"
                "/info - Bot information\n\n"
                "<b>You can also use buttons</b> below"
            )
            keyboard = get_keyboard()

        elif command == '/hello':
            response = f"Hello, {first_name}! Nice to see you!\nHow are you?"
            keyboard = None

        elif command == '/info':
            response = (
                "<b>Bot Information:</b>\n\n"
                "<b>Name:</b> K2NeuroAssist_bot\n"
                "<b>Description:</b> Demonstration bot\n"
                "<b>Function:</b> Responds 'Hello' to all messages\n\n"
                "Bot created for learning Telegram Bot API."
            )
            keyboard = None

        else:
            response = (
                f"I don't know command <code>{text}</code>\n\n"
                f"But I'll still say: <b>Hello, {first_name}!</b>\n"
                f"Use /help for command list."
            )
            keyboard = None

    else:
        # Process regular messages and buttons
        text_lower = text.lower()

        if 'hello' in text_lower or 'привет' in text_lower or text == 'Say Hello':
            response = f"Hello hello, {first_name}!\nHow are you doing?"

        elif 'information' in text_lower or 'информация' in text_lower or text == 'Information':
            response = (
                "<b>Information:</b>\n\n"
                "This is a demonstration bot that:\n"
                "1. Responds 'Hello' to all messages\n"
                "2. Has basic commands\n"
                "3. Works on Telegram Bot API\n\n"
                "Use /help for all commands."
            )

        elif 'help' in text_lower or 'помощь' in text_lower or text == 'Help':
            response = (
                "<b>Help:</b>\n\n"
                "Just send me <b>any message</b> and I'll respond!\n"
                "Or use commands:\n"
                "• /start - restart the bot\n"
                "• /hello - personal greeting\n"
                "• /info - bot information"
            )

        elif 'refresh' in text_lower or 'обновить' in text_lower or text == 'Refresh':
            response = f"Refreshed, {first_name}!\nBot is working normally."

        else:
            # Response to any other message
            responses = [
                f"Hello, {first_name}!",
                f"Greetings, {first_name}!",
                f"Welcome, {first_name}!",
                f"Good to see you, {first_name}!",
                f"Hello! How are you, {first_name}?"
            ]
            response = random.choice(responses)

        keyboard = None

    return {
        'chat_id': chat_id,
        'text': response,
        'keyboard': keyboard
    }


def check_bot_info():
    """Check bot information from Telegram API"""
    try:
        url = f'{BASE_URL}/getMe'
        # param: timeout - request timeout in seconds
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('ok'):
            bot_info = data['result']
            print(f"SUCCESS: Bot connected successfully!")
            print(f"Bot name: {bot_info.get('first_name')}")
            print(f"Username: @{bot_info.get('username')}")
            print(f"Bot ID: {bot_info.get('id')}")
            print("-" * 50)
            return True
        else:
            print(f"ERROR: {data.get('description')}")
            return False

    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False


def main():
    """Main bot loop"""
    print("=" * 50)
    print("STARTING K2NeuroAssist_bot")
    print("=" * 50)

    # Check bot connection
    if not check_bot_info():
        print("ERROR: Failed to connect to bot. Check token and internet.")
        return

    print("SUCCESS: Bot ready to work!")
    print("Open Telegram and find @K2NeuroAssist_bot")
    print("Start conversation with /start command")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    last_update_id = None
    processed_updates = set()  # Avoid duplicate processing

    while True:
        try:
            # Get updates
            updates = get_updates(last_update_id)

            for update in updates:
                update_id = update['update_id']

                # Check if update already processed
                if update_id in processed_updates:
                    continue

                processed_updates.add(update_id)

                # Process the update
                result = process_update(update)

                if result:
                    # Send response
                    send_message(
                        result['chat_id'],
                        result['text'],
                        result['keyboard']
                    )

                # Update last processed update ID
                last_update_id = update_id + 1

                # Clean old IDs from memory
                if len(processed_updates) > 1000:
                    processed_updates = set(list(processed_updates)[-500:])

            # Small delay to avoid overload
            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n" + "=" * 50)
            print("STOP: Bot stopped by user")
            print("=" * 50)
            break

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait before retry


if __name__ == '__main__':
    # Check if requests library is installed
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' library not installed!")
        print("Install with: pip install requests")
        exit(1)

    main()