import logging
import time
import threading
import requests

from modules.invite_manager import use_invite

from modules.csv_storage import init_csv_files, load_data
from modules.telegram_bot import (
    send_message,
    get_main_keyboard,
    handle_message,
    handle_callback_query
)
from modules.handlers import (
    handle_task_command,
    handle_set_status_command,
    handle_list_tasks,
    handle_list_users,
    handle_add_user,
    handle_remove_user
)
from modules.api_server import run_api_server
from modules.auth import is_authorized, is_admin

TOKEN = ''

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_updates(offset=None):
    url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
    params = {'timeout': 30, 'offset': offset} if offset else {'timeout': 30}
    try:
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        return data.get('result', []) if data.get('ok') else []
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
        return []

def main():
    init_csv_files()
    users_by_username, users_by_id, tasks = load_data()

    threading.Thread(target=run_api_server, args=(8000,), daemon=True).start()
    last_update_id = None
    processed = set()

    logger.info("Бот запущен.")

    while True:
        try:
            updates = get_updates(last_update_id)
            for update in updates:
                uid = update['update_id']
                if uid in processed:
                    continue
                processed.add(uid)

                if 'callback_query' in update:
                    handle_callback_query(
                        update['callback_query'],
                        tasks,
                        users_by_id,
                        TOKEN,
                        handle_set_status_command
                    )
                elif 'message' in update and 'text' in update['message']:
                    message = update['message']
                    chat_id = message['chat']['id']
                    text = message.get('text', '').strip()
                    telegram_user = message.get('from', {})
                    telegram_username = telegram_user.get('username')

                    # Обработка приглашений
                    if text.startswith("/start invite_"):
                        invite_code = text.replace("/start invite_", "").strip()
                        telegram_user_id = telegram_user.get('id')
                        full_name = (
                            (telegram_user.get('first_name') or '') + ' ' +
                            (telegram_user.get('last_name') or '')
                        ).strip() or telegram_username

                        if not telegram_username:
                            send_message(
                                chat_id,
                                "Для регистрации необходимо установить username в Telegram.",
                                TOKEN
                            )
                        else:
                            users_by_username, users_by_id, tasks = load_data()
                            success, msg = use_invite(
                                invite_code, telegram_user_id, telegram_username, full_name,
                                users_by_id, users_by_username
                            )
                            is_new_admin = False  # новый пользователь — не админ
                            if success:
                                send_message(chat_id, msg, TOKEN, get_main_keyboard(is_new_admin))
                            else:
                                send_message(chat_id, msg, TOKEN)
                        continue  # пропустить обычную обработку

                    # Обычная обработка
                    if text == "/start":
                        user_record = is_authorized(telegram_username, users_by_username)
                        admin = is_admin(user_record)
                        send_message(chat_id, "Выберите действие:", TOKEN, get_main_keyboard(admin))
                    else:
                        handle_message(
                            message,
                            users_by_username,
                            users_by_id,
                            tasks,
                            TOKEN,
                            handle_task_command,
                            handle_set_status_command,
                            handle_list_tasks,
                            handle_list_users,
                            handle_add_user,
                            handle_remove_user
                        )

                last_update_id = uid + 1
                if len(processed) > 1000:
                    processed = set(list(processed)[-500:])

            time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Бот остановлен.")
            break
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()