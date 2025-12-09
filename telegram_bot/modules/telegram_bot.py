import json
import logging

logger = logging.getLogger(__name__)
user_state = {}

def send_message(chat_id, text, token, reply_markup=None):
    import requests
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def get_main_keyboard(is_admin=False):
    keyboard = [
        ["Просмотр задачи", "Изменить статус"],
        ["Список всех задач", "Список пользователей"]
    ]
    if is_admin:
        keyboard.append(["Добавить пользователя", "Удалить пользователя"])
        keyboard.append(["Создать приглашение", "Список приглашений"])
    keyboard.append(["Помощь"])
    return json.dumps({
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False
    })

def get_status_inline_keyboard(task_id):
    return json.dumps({
        "inline_keyboard": [
            [
                {"text": "В работе", "callback_data": f"set_status:{task_id}:in_progress"},
                {"text": "Завершена", "callback_data": f"set_status:{task_id}:done"}
            ],
            [{"text": "Отменена (To Do)", "callback_data": f"set_status:{task_id}:todo"}],
            [{"text": "← Отмена", "callback_data": "cancel"}]
        ]
    })

def get_back_button():
    return json.dumps({
        "inline_keyboard": [[{"text": "← Вернуться в меню", "callback_data": "cancel"}]]
    })

def handle_message(
    message, users_by_username, users_by_id, tasks, token,
    handle_task, handle_set_status, handle_list_tasks, handle_list_users,
    handle_add_user, handle_remove_user
):
    chat_id = message['chat']['id']
    text = message.get('text', '').strip()
    user = message.get('from', {})
    telegram_user_id = user.get('id')
    telegram_username = user.get('username')
    first_name = user.get('first_name', '')

    from .auth import is_authorized, is_admin
    user_record = is_authorized(telegram_username, users_by_username)
    admin = is_admin(user_record)

    if not telegram_username:
        send_message(chat_id, "У вас не установлен username в Telegram. Пожалуйста, задайте его в настройках.", token)
        return

    if not user_record:
        send_message(chat_id, "Ваш аккаунт не зарегистрирован. Обратитесь к администратору.", token)
        return

    # Обработка состояний
    if telegram_user_id in user_state:
        state = user_state[telegram_user_id]
        if state['state'] == 'awaiting_task_id_for_status':
            if text.isdigit():
                task_id = int(text)
                if task_id in tasks:
                    user_state[telegram_user_id] = {'state': 'selecting_status', 'task_id': task_id}
                    send_message(chat_id, f"Выберите статус для задачи #{task_id}:", token, get_status_inline_keyboard(task_id))
                else:
                    send_message(chat_id, "Задача не найдена.", token, get_back_button())
            else:
                send_message(chat_id, "Введите корректный ID задачи (число).", token, get_back_button())
            return

        elif state['state'] == 'awaiting_task_id_for_view':
            if text.isdigit():
                response = handle_task(int(text), tasks, users_by_username)
                send_message(chat_id, response, token, get_main_keyboard(admin))
            else:
                send_message(chat_id, "Некорректный ID.", token, get_main_keyboard(admin))
            user_state.pop(telegram_user_id, None)
            return

        elif state['state'] == 'awaiting_new_user_data':
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                send_message(chat_id, "Формат: <code>username роль [ФИО]</code>\nПример: testuser member Иван Иванов", token, get_back_button())
                return
            new_username, role = parts[0], parts[1]
            full_name = parts[2] if len(parts) > 2 else new_username
            if role not in ['admin', 'manager', 'member', 'viewer']:
                send_message(chat_id, "Недопустимая роль. Допустимо: admin, manager, member, viewer", token, get_back_button())
                return
            # Предполагаем, что админ добавляет чужого — ID пока неизвестен → запрещаем
            send_message(chat_id, "Добавление по username невозможно без ID. Используйте веб-интерфейс или расширьте API.", token, get_main_keyboard(admin))
            user_state.pop(telegram_user_id, None)
            return

        elif state['state'] == 'awaiting_username_to_remove':
            target = text.strip().lstrip('@')
            response = handle_remove_user(target, users_by_id, users_by_username)
            send_message(chat_id, response, token, get_main_keyboard(admin))
            user_state.pop(telegram_user_id, None)
            return

    # Главное меню
    if text == "/start":
        send_message(chat_id, "Выберите действие:", token, get_main_keyboard(admin))
        return

    if text == "Помощь":
        msg = (
            "<b>Доступные команды:</b>\n"
            "• Просмотр задачи — введите ID\n"
            "• Изменить статус — выберите задачу и статус\n"
            "• Список задач и пользователей\n"
        )
        if admin:
            msg += "• Добавить/удалить пользователя (только админ)\n"
        send_message(chat_id, msg, token, get_main_keyboard(admin))
        return

    if text == "Список всех задач":
        send_message(chat_id, handle_list_tasks(tasks, users_by_username), token, get_main_keyboard(admin))
        return

    if text == "Список пользователей":
        send_message(chat_id, handle_list_users(users_by_username), token, get_main_keyboard(admin))
        return

    if text == "Просмотр задачи":
        user_state[telegram_user_id] = {'state': 'awaiting_task_id_for_view'}
        send_message(chat_id, "Введите ID задачи:", token, get_back_button())
        return

    if text == "Изменить статус":
        user_state[telegram_user_id] = {'state': 'awaiting_task_id_for_status'}
        send_message(chat_id, "Введите ID задачи для изменения статуса:", token, get_back_button())
        return

    if admin:
        if text == "Добавить пользователя":
            send_message(
                chat_id,
                "Введите данные в формате:\n<code>username роль [ФИО]</code>\n"
                "Пример: <code>ivan member Иван Иванов</code>\n\n"
                "⚠️ Примечание: в текущей версии добавление через бота ограничено (требуется Telegram ID). "
                "Рекомендуется использовать веб-панель.",
                token,
                get_back_button()
            )
            user_state[telegram_user_id] = {'state': 'awaiting_new_user_data'}
            return

        if text == "Удалить пользователя":
            send_message(chat_id, "Введите username пользователя для удаления (с @ или без):", token, get_back_button())
            user_state[telegram_user_id] = {'state': 'awaiting_username_to_remove'}
            return

        if text == "Создать приглашение":
            from .invite_manager import create_invite
            code = create_invite(telegram_username)
            bot_name = "CaseK2NeuroTechDevelopmentAssistant_K11_bot"
            link = f"https://t.me/{bot_name}?start=invite_{code}"
            send_message(
                chat_id,
                f"Создана пригласительная ссылка:\n\n{link}\n\nОтправьте её новому пользователю.",
                token,
                get_main_keyboard(admin)
            )
            return

        if text == "Список приглашений":
            from .handlers import handle_list_invites
            send_message(chat_id, handle_list_invites(), token, get_main_keyboard(admin))
            return

    send_message(chat_id, "Неизвестная команда.", token, get_main_keyboard(admin))

def handle_callback_query(callback_query, tasks, users_by_id, token, handle_set_status_func):
    chat_id = callback_query['message']['chat']['id']
    telegram_user_id = callback_query['from']['id']
    data = callback_query['data']

    if data == "cancel":
        from .auth import is_authorized, is_admin
        username = callback_query['from'].get('username')
        user_record = is_authorized(username, {})  # только для проверки роли — данные загружены глобально
        # Но роль берём из глобального users — в реальности нужно передавать users_by_username
        # Для упрощения: в основном цикле мы обновим клавиатуру по текущему пользователю
        # Здесь временно считаем, что admin = True если нужно
        send_message(chat_id, "Действие отменено.", token)
        return

    if data.startswith("set_status:"):
        try:
            _, task_id_str, new_status = data.split(":")
            task_id = int(task_id_str)
            telegram_username = callback_query['from'].get('username')
            if not telegram_username:
                send_message(chat_id, "Ошибка: нет username.", token)
                return
            response = handle_set_status_func(task_id, new_status, tasks, telegram_username)
            send_message(chat_id, response, token)
        except Exception as e:
            logger.error(f"Ошибка callback: {e}")
            send_message(chat_id, "Ошибка обработки.", token)