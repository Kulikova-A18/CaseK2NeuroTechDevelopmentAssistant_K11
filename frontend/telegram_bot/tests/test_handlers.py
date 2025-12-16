"""
Tests for message handlers.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext
from modules.session_manager import UserSession


@pytest.fixture
def mock_message():
    """Create mock message."""
    user = User(id=123, first_name="Test", is_bot=False)
    chat = Chat(id=456, type="private")
    message = AsyncMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.text = "/start"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    """Create mock callback query."""
    user = User(id=123, first_name="Test", is_bot=False)
    chat = Chat(id=456, type="private")
    message = AsyncMock(spec=Message)
    message.chat = chat
    message.edit_text = AsyncMock()
    
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = user
    callback.message = message
    callback.data = "test:data"
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_state():
    """Create mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_data = AsyncMock()
    return state


@pytest.fixture
def user_session():
    """Create fresh user session."""
    return UserSession()


@pytest.mark.asyncio
async def test_cmd_start_authenticated(mock_message, mock_state):
    """Test /start command with successful authentication."""
    from modules.handlers import cmd_start
    
    # Mock API response
    mock_auth_result = {
        'authenticated': True,
        'access_token': 'test_token_123',
        'user': {
            'full_name': 'Test User',
            'telegram_username': '@testuser',
            'role': 'member'
        }
    }
    
    with patch('modules.handlers.APIClient') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.__aenter__.return_value = mock_api
        mock_api.__aexit__.return_value = None
        mock_api.authenticate.return_value = mock_auth_result
        mock_api_class.return_value = mock_api
        
        await cmd_start(mock_message, mock_state)
        
        # Check that message was answered
        assert mock_message.answer.call_count >= 1
        
        # Check welcome message
        first_call_args = mock_message.answer.call_args_list[0]
        call_text = first_call_args[0][0]
        assert "Добро пожаловать в Task Manager Bot" in call_text
        assert "Вы успешно вошли" in call_text


@pytest.mark.asyncio
async def test_cmd_start_not_authenticated(mock_message, mock_state):
    """Test /start command without authentication."""
    from modules.handlers import cmd_start
    
    # Mock empty API response
    with patch('modules.handlers.APIClient') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.__aenter__.return_value = mock_api
        mock_api.__aexit__.return_value = None
        mock_api.authenticate.return_value = {}
        mock_api_class.return_value = mock_api
        
        await cmd_start(mock_message, mock_state)
        
        # Check that message was answered twice (welcome + login prompt)
        assert mock_message.answer.call_count >= 2
        
        # Check login prompt
        second_call_args = mock_message.answer.call_args_list[1]
        call_text = second_call_args[0][0]
        assert "необходимо войти в систему" in call_text
        assert "/login" in call_text


@pytest.mark.asyncio
async def test_cmd_login_success(mock_message, mock_state):
    """Test /login command with success."""
    from modules.handlers import cmd_login
    from modules.session_manager import user_sessions
    
    # Mock API response
    mock_auth_result = {
        'authenticated': True,
        'access_token': 'test_token_456',
        'user': {
            'full_name': 'Test User',
            'telegram_username': '@testuser',
            'role': 'admin'
        }
    }
    
    with patch('modules.handlers.APIClient') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.__aenter__.return_value = mock_api
        mock_api.__aexit__.return_value = None
        mock_api.authenticate.return_value = mock_auth_result
        mock_api_class.return_value = mock_api
        
        await cmd_login(mock_message, mock_state)
        
        # Check that session was saved
        session = user_sessions.get_session(123)
        assert session['access_token'] == 'test_token_456'
        assert session['user_info'] == mock_auth_result
        
        # Check success message
        call_text = mock_message.answer.call_args[0][0]
        assert "Успешный вход" in call_text
        assert "Test User" in call_text
        assert "Admin" in call_text


@pytest.mark.asyncio
async def test_cmd_tasks_not_authenticated(mock_message, mock_state):
    """Test tasks command without authentication."""
    from modules.handlers import cmd_tasks
    from modules.session_manager import user_sessions
    
    # Clear any existing session
    user_sessions.clear_session(123)
    
    mock_message.text = "Задачи"
    
    await cmd_tasks(mock_message, mock_state)
    
    # Check unauthorized message
    call_text = mock_message.answer.call_args[0][0]
    assert "Вы не авторизованы" in call_text
    assert "/login" in call_text


@pytest.mark.asyncio
async def test_cmd_profile_not_authenticated(mock_message, mock_state):
    """Test profile command without authentication."""
    from modules.handlers import cmd_profile
    from modules.session_manager import user_sessions
    
    # Clear any existing session
    user_sessions.clear_session(123)
    
    mock_message.text = "Профиль"
    
    await cmd_profile(mock_message, mock_state)
    
    # Check unauthorized message
    call_text = mock_message.answer.call_args[0][0]
    assert "Вы не авторизованы" in call_text
    assert "/login" in call_text


@pytest.mark.asyncio
async def test_cmd_help(mock_message):
    """Test help command."""
    from modules.handlers import cmd_help
    
    mock_message.text = "/help"
    
    await cmd_help(mock_message)
    
    # Check help message
    call_text = mock_message.answer.call_args[0][0]
    assert "Справка по командам" in call_text
    assert "/start" in call_text
    assert "/login" in call_text
    assert "/tasks" in call_text
    assert "/newtask" in call_text
    assert "/analyze" in call_text
    assert "/export" in call_text
    assert "/profile" in call_text


@pytest.mark.asyncio
async def test_cmd_cancel(mock_message, mock_state):
    """Test cancel command."""
    from modules.handlers import cmd_cancel
    
    mock_message.text = "Отмена"
    
    await cmd_cancel(mock_message, mock_state)
    
    # Check cancel message
    call_text = mock_message.answer.call_args[0][0]
    assert "Действие отменено" in call_text
    assert "Возвращаюсь в главное меню" in call_text
    
    # Check state was cleared
    mock_state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_back_to_menu(mock_message, mock_state):
    """Test back to menu command."""
    from modules.handlers import cmd_back_to_menu
    
    mock_message.text = "Назад в меню"
    
    await cmd_back_to_menu(mock_message, mock_state)
    
    # Check back message
    call_text = mock_message.answer.call_args[0][0]
    assert "Возвращаюсь в главное меню" in call_text
    
    # Check state was cleared
    mock_state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_handle_unknown_message(mock_message):
    """Test unknown message handler."""
    from modules.handlers import handle_unknown_message
    
    mock_message.text = "random unknown text"
    
    await handle_unknown_message(mock_message)
    
    # Check unknown message response
    call_text = mock_message.answer.call_args[0][0]
    assert "Я не понял ваше сообщение" in call_text
    assert "/help" in call_text