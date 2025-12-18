"""
Message handlers for Telegram bot.
"""

import logging
from datetime import datetime
from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from modules.api_client import APIClient
from modules.session_manager import user_sessions
from modules.formatters import MessageFormatter
from modules.keyboards import *
from modules.states import TaskStates, AnalysisStates
from modules.utils import load_and_show_tasks, convert_to_excel, csv_to_excel

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


logger = logging.getLogger(__name__)



async def cmd_start(message: types.Message, state: FSMContext):
    """
    Handler for /start command.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"user_{user_id}"
    full_name = message.from_user.full_name or f"Пользователь {user_id}"
    
    # Welcome message
    welcome_text = (
        f"Добро пожаловать в Task Manager Bot!\n\n"
        f"Я помогу вам управлять задачами вашей команды:\n"
        f"- Создавать и отслеживать задачи\n"
        f"- Получать уведомления об изменениями\n"
        f"- Анализировать продуктивность с помощью AI\n"
        f"- Экспортировать данные в CSV и Excel\n\n"
        f"Для начала работы используйте команду /login\n"
        f"Или выберите действие в меню ниже"
    )
    
    # Try automatic authentication
    async with APIClient() as api_client:
        auth_result = await api_client.authenticate(username, full_name)
        
        if auth_result and auth_result.get('authenticated'):
            # Save session
            session_data = {
                'access_token': auth_result.get('access_token'),
                'user_info': auth_result
            }
            user_sessions.set_session(user_id, session_data)
            
            logger.info(f"User {user_id} ({username}) successfully authenticated")
            logger.debug(f"Token saved: {auth_result.get('access_token', '')[:10]}...")
            
            welcome_text += f"\n\nВы успешно вошли как {auth_result.get('user', {}).get('full_name', username)}"
            await message.answer(
                welcome_text,
                reply_markup=Keyboards.get_main_menu()
            )
        else:
            # Show menu without authorization
            logger.info(f"User {user_id} ({username}) not authenticated")
            await message.answer(
                welcome_text
            )
            await message.answer(
                "Для использования всех функций бота необходимо войти в систему.\n"
                "Используйте команду /login",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[[types.KeyboardButton(text="/login")]],
                    resize_keyboard=True
                )
            )


async def cmd_login(message: types.Message, state: FSMContext):
    """
    Handler for /login command.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"user_{user_id}"
    full_name = message.from_user.full_name or f"Пользователь {user_id}"
    
    await message.answer(
        "Пытаюсь войти в систему..."
    )
    
    async with APIClient() as api_client:
        auth_result = await api_client.authenticate(username, full_name)
        
        if auth_result and auth_result.get('authenticated'):
            # Save session
            session_data = {
                'access_token': auth_result.get('access_token'),
                'user_info': auth_result
            }
            user_sessions.set_session(user_id, session_data)
            
            logger.info(f"User {user_id} ({username}) successfully logged in")
            logger.debug(f"Token saved: {auth_result.get('access_token', '')[:10]}...")
            
            user_data = auth_result.get('user', {})
            await message.answer(
                f"Успешный вход!\n\n"
                f"Добро пожаловать, {user_data.get('full_name', username)}!\n"
                f"Ваша роль: {user_data.get('role', 'member').title()}\n\n"
                f"Теперь вы можете использовать все функции бота.",
                reply_markup=Keyboards.get_main_menu()
            )
        else:
            logger.warning(f"User {user_id} ({username}) failed to login")
            await message.answer(
                "Не удалось войти в систему\n\n"
                "Возможные причины:\n"
                "- Ваш Telegram не зарегистрирован в системе\n"
                "- Система недоступна\n"
                "- Ошибка аутентификации\n\n"
                "Обратитесь к администратору для регистрации."
            )


async def cmd_tasks(message: types.Message, state: FSMContext):
    """
    Handler for tasks command.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    logger.info(f"Tasks request from user {user_id}, token found: {token is not None}")
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Show tasks menu
    await message.answer(
        "Меню задач",
        reply_markup=Keyboards.get_tasks_menu()
    )


async def cmd_my_tasks(message: types.Message, state: FSMContext):
    """
    Handler for my tasks command.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Get user info for filtering
    user_info = user_sessions.get_user_info(user_id)
    username = None
    if user_info:
        user_data = user_info.get('user', {})
        username = user_data.get('telegram_username')
    
    filters = {}
    if username:
        filters['assignee'] = username
    
    await load_and_show_tasks(message, token, filters, "Мои задачи")


async def cmd_all_tasks(message: types.Message, state: FSMContext):
    """
    Handler for all tasks command.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    await load_and_show_tasks(message, token, {}, "Все задачи")


async def cmd_filter_search(message: types.Message, state: FSMContext):
    """
    Handler for task filter search.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Show task filters
    await message.answer(
        "Поиск задач по фильтрам\n\n"
        "Выберите фильтры для поиска задач:",
        reply_markup=Keyboards.get_task_filters_keyboard()
    )


async def cmd_new_task(message: types.Message, state: FSMContext):
    """
    Handler for new task creation.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    logger.info(f"New task request from user {user_id}, token found: {token is not None}")
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    await state.set_state(TaskStates.waiting_for_title)
    await message.answer(
        "Создание новой задачи\n\n"
        "Введите заголовок задачи:",
        reply_markup=Keyboards.get_cancel_keyboard()
    )


async def process_task_title(message: types.Message, state: FSMContext):
    """
    Handler for receiving task title.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await state.clear()
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Проверка на команду отмены
    if message.text.lower() in ["/cancel", "отмена", "cancel"]:
        await state.clear()
        await message.answer(
            "Создание задачи отменено",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Save title to state
    title = message.text
    await state.update_data(title=title)
    
    # Move to next state
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer(
        f"Заголовок сохранен: {title}\n\n"
        "Введите описание задачи (или напишите 'пропустить', чтобы оставить пустым):",
        reply_markup=Keyboards.get_cancel_keyboard()
    )
    

async def process_task_description(message: types.Message, state: FSMContext):
    """
    Handler for receiving task description.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await state.clear()
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    if message.text.lower() in ["/cancel", "отмена", "cancel"]:
        await state.clear()
        await message.answer(
            "Создание задачи отменено",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    description = message.text
    await state.update_data(description=description)
    
    data = await state.get_data()
    title = data.get('title', '')
    description = data.get('description', '')
    
    try:
        async with APIClient() as api_client:
            task_data = {
                'title': title,
                'description': description,
                'status': 'todo'
            }
            
            response = await api_client.create_task(token, task_data)

            await message.answer(
                "Задача успешно создана!",
                reply_markup=Keyboards.get_main_menu()
            )
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await message.answer(
            "Не удалось создать задачу. Попробуйте еще раз.",
            reply_markup=Keyboards.get_main_menu()
        )
    
    finally:
        await state.clear()


async def cmd_change_task_status(message: types.Message, state: FSMContext):
    """
    Handler for changing task status.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    logger.info(f"Change task status request from user {user_id}, token found: {token is not None}")
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Запрашиваем ID задачи
    await state.set_state(TaskStates.waiting_for_task_id)
    await message.answer(
        "Изменение статуса задачи\n\n"
        "Введите ID задачи, статус которой хотите изменить:",
        reply_markup=Keyboards.get_cancel_keyboard()
    )

async def process_task_id_for_status(message: types.Message, state: FSMContext):
    """
    Handler for receiving task ID for status change.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await state.clear()
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Проверка на команду отмены
    if message.text.lower() in ["/cancel", "отмена", "cancel"]:
        await state.clear()
        await message.answer(
            "Изменение статуса отменено",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Проверяем, что введен номер
    try:
        task_id = int(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректный ID задачи (число).",
            reply_markup=Keyboards.get_cancel_keyboard()
        )
        return
    
    # Проверяем существование задачи
    async with APIClient() as api_client:
        tasks_response = await api_client.get_tasks(token, {})
        
        if not tasks_response:
            await state.clear()
            await message.answer(
                "Не удалось получить список задач.\n"
                "Попробуйте позже или обратитесь к администратору.",
                reply_markup=Keyboards.get_main_menu()
            )
            return
        
        # FIX: Проверяем тип ответа
        if isinstance(tasks_response, dict):
            # Это словарь с ключом 'tasks'
            if 'error' in tasks_response:
                error_msg = tasks_response.get('error', 'Неизвестная ошибка')
                await state.clear()
                await message.answer(
                    f"Ошибка при получении задач: {error_msg}\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    reply_markup=Keyboards.get_main_menu()
                )
                return
            tasks = tasks_response.get('tasks', [])
        elif isinstance(tasks_response, list):
            # Это уже список задач
            tasks = tasks_response
        else:
            # Неизвестный формат ответа
            await state.clear()
            await message.answer(
                "Неверный формат ответа от сервера.\n"
                "Попробуйте позже или обратитесь к администратору.",
                reply_markup=Keyboards.get_main_menu()
            )
            return
        
        # Ищем задачу по ID
        task_exists = False
        for task in tasks:
            # Преобразуем task_id из задачи в строку для сравнения
            task_task_id = str(task.get('task_id', ''))
            if task_task_id == str(task_id):
                task_exists = True
                break
    
    if not task_exists:
        await state.clear()
        await message.answer(
            f"Задача с ID {task_id} не найдена.\n"
            "Проверьте правильность ID и попробуйте еще раз.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Показываем клавиатуру выбора статуса
    await state.clear()
    await message.answer(
        f"Выберите новый статус для задачи #{task_id}:",
        reply_markup=Keyboards.get_task_status_keyboard(task_id)
    )
async def handle_status_change_callback(query: types.CallbackQuery):
    """
    Handler for task status change callback.
    
    @param query: CallbackQuery object
    """
    user_id = query.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await query.answer("Вы не авторизованы. Используйте /login")
        return
    
    # Разбираем callback_data
    data = query.data.split(":")
    if len(data) != 3:
        await query.answer("Ошибка данных")
        return
    
    action, task_id, new_status = data
    
    if action != "change_status":
        return
    
    # Обновляем статус задачи
    async with APIClient() as api_client:
        try:
            # Подготавливаем данные для обновления
            update_data = {"status": new_status}
            
            # Отправляем запрос на обновление
            response = await api_client.update_task(token, int(task_id), update_data)
            
            # FIX: Проверяем тип response перед использованием
            if not response:
                # response is None or empty
                await query.message.edit_text(
                    f"Ошибка при изменении статуса задачи #{task_id}:\n"
                    f"Пустой ответ от сервера\n\n"
                    f"Попробуйте еще раз или обратитесь к администратору.",
                    reply_markup=None
                )
                await query.answer("Ошибка при изменении статуса")
                return
            
            if isinstance(response, dict):
                # Это словарь
                if 'error' in response:
                    error_msg = response.get('error', 'Неизвестная ошибка')
                    await query.message.edit_text(
                        f"Ошибка при изменении статуса задачи #{task_id}:\n"
                        f"{error_msg}\n\n"
                        f"Попробуйте еще раз или обратитесь к администратору.",
                        reply_markup=None
                    )
                    await query.answer("Ошибка при изменении статуса")
                    return
                else:
                    # Успешный ответ в формате словаря
                    # Получаем названия статусов для отображения
                    status_names = {
                        "todo": "к выполнению",
                        "in_progress": "в процессе",
                        "in_review": "на проверке",
                        "done": "завершено",
                        "paused": "отложено",
                        "cancelled": "отменено"
                    }
                    
                    status_display = status_names.get(new_status, new_status)
                    
                    await query.message.edit_text(
                        f"Статус задачи #{task_id} успешно изменен на:\n"
                        f"{status_display.upper()}\n\n"
                        f"Используйте /tasks для просмотра обновленного списка задач.",
                        reply_markup=None
                    )
                    
                    # Отправляем подтверждение
                    await query.answer(f"Статус изменен на {status_display}")
                    
                    # Логируем действие
                    logger.info(f"User {user_id} changed status of task #{task_id} to {new_status}")
                    return
            
            elif isinstance(response, bool):
                # Это булево значение (например, True при успехе)
                if response:
                    status_names = {
                        "todo": "к выполнению",
                        "in_progress": "в процессе",
                        "in_review": "на проверке",
                        "done": "завершено",
                        "paused": "отложено",
                        "cancelled": "отменено"
                    }
                    
                    status_display = status_names.get(new_status, new_status)
                    
                    await query.message.edit_text(
                        f"Статус задачи #{task_id} успешно изменен на:\n"
                        f"{status_display.upper()}\n\n"
                        f"Используйте /tasks для просмотра обновленного списка задач.",
                        reply_markup=None
                    )
                    
                    await query.answer(f"Статус изменен на {status_display}")
                    logger.info(f"User {user_id} changed status of task #{task_id} to {new_status}")
                else:
                    await query.message.edit_text(
                        f"Ошибка при изменении статуса задачи #{task_id}:\n"
                        f"Сервер вернул False\n\n"
                        f"Попробуйте еще раз или обратитесь к администратору.",
                        reply_markup=None
                    )
                    await query.answer("Ошибка при изменении статуса")
                return
            
            else:
                # Неизвестный формат ответа
                await query.message.edit_text(
                    f"Неизвестный формат ответа от сервера для задачи #{task_id}.\n"
                    f"Тип ответа: {type(response)}\n\n"
                    f"Обратитесь к администратору.",
                    reply_markup=None
                )
                await query.answer("Ошибка формата ответа")
                
        except Exception as e:
            logger.error(f"Error changing task status: {e}", exc_info=True)
            await query.message.edit_text(
                f"Произошла ошибка при изменении статуса:\n"
                f"{str(e)}\n\n"
                f"Попробуйте еще раз позже.",
                reply_markup=None
            )
            await query.answer("Произошла ошибка")

async def handle_cancel_status_change_callback(query: types.CallbackQuery):
    """
    Handler for cancel status change callback.
    
    @param query: CallbackQuery object
    """
    data = query.data.split(":")
    if len(data) == 2 and data[0] == "cancel_status_change":
        task_id = data[1]
        await query.message.edit_text(
            f"Изменение статуса задачи #{task_id} отменено.\n\n"
            f"Возвращайтесь в главное меню.",
            reply_markup=None
        )
        await query.answer("Изменение статуса отменено")


async def cmd_analyze(message: types.Message, state: FSMContext):
    """
    Handler for AI analysis command.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    logger.info(f"AI analysis request from user {user_id}, token found: {token is not None}")
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    await message.answer(
        "AI Анализ задач\n\n"
        "Выберите период для анализа:",
        reply_markup=Keyboards.get_analysis_period_keyboard()
    )


async def cmd_export(message: types.Message, state: FSMContext):
    """
    Handler for export command.
    
    @param message: Message object
    @param state: FSM context
    """
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)
    
    logger.info(f"Export request from user {user_id}, token found: {token is not None}")
    
    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в системе.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    await message.answer(
        "Экспорт задач\n\n"
        "Выберите формат экспорта:",
        reply_markup=Keyboards.get_export_format_keyboard()
    )


async def cmd_profile(message: types.Message, state: FSMContext):
    """
    Handler for profile command.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    
    user_id = message.from_user.id
    user_info = user_sessions.get_user_info(user_id)
    
    logger.info(f"Profile request from user {user_id}, info found: {user_info is not None}")
    
    if not user_info:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return
    
    # Format user information
    formatter = MessageFormatter()
    profile_text = formatter.format_user_info(user_info)
    
    await message.answer(
        profile_text,
        reply_markup=Keyboards.get_main_menu()
    )


async def cmd_back_to_menu(message: types.Message, state: FSMContext):
    """
    Handler for back to menu command.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    await message.answer(
        "Возвращаюсь в главное меню.",
        reply_markup=Keyboards.get_main_menu()
    )


async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Handler for cancel action.
    
    @param message: Message object
    @param state: FSM context
    """
    await state.clear()
    await message.answer(
        "Действие отменено\n\n"
        "Возвращаюсь в главное меню.",
        reply_markup=Keyboards.get_main_menu()
    )


async def cmd_help_button(message: types.Message):
    """
    Handler for help button.
    
    @param message: Message object
    """
    await cmd_help(message)


async def cmd_help(message: types.Message):
    """
    Handler for /help command.
    
    @param message: Message object
    """
    help_text = (
        "Справка по командам\n\n"
        "Основные команды:\n"
        "/start - Запустить бота\n"
        "/login - Войти в систему\n"
        "/tasks - Задачи\n"
        "/newtask - Создать задачу\n"
        "/analyze - AI анализ задач\n"
        "/export - Экспорт задач\n"
        "/profile - Мой профиль\n"
        "/changestatus - Изменить статус задачи\n\n"
        "Быстрые действия:\n"
        "Используйте кнопки меню для быстрого доступа к функциям."
    )
    await message.answer(help_text, reply_markup=Keyboards.get_main_menu())


async def handle_unknown_message(message: types.Message):
    """
    Handler for unknown messages.
    
    @param message: Message object
    """
    logger.info(f"Received unknown message: {message.text} from user {message.from_user.id}")
    
    await message.answer(
        "Я не понял ваше сообщение\n\n"
        "Используйте команды из меню или напишите /help для справки.",
        reply_markup=Keyboards.get_main_menu()
    )
