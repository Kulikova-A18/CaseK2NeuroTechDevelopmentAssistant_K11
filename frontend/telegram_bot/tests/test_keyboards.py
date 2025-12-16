"""
Tests for keyboard generators.
"""

from modules.keyboards import Keyboards


def test_get_main_menu():
    """Test main menu keyboard creation."""
    keyboard = Keyboards.get_main_menu()
    
    assert len(keyboard.keyboard) == 3  # 3 rows
    
    # Check button texts
    assert keyboard.keyboard[0][0].text == "Задачи"
    assert keyboard.keyboard[0][1].text == "Создать задачу"
    assert keyboard.keyboard[1][0].text == "AI Анализ"
    assert keyboard.keyboard[1][1].text == "Экспорт"
    assert keyboard.keyboard[2][0].text == "Профиль"
    assert keyboard.keyboard[2][1].text == "Помощь"
    
    assert keyboard.resize_keyboard is True
    assert keyboard.input_field_placeholder == "Выберите действие..."


def test_get_tasks_menu():
    """Test tasks menu keyboard creation."""
    keyboard = Keyboards.get_tasks_menu()
    
    assert len(keyboard.keyboard) == 3  # 3 rows
    
    # Check button texts
    assert keyboard.keyboard[0][0].text == "Мои задачи"
    assert keyboard.keyboard[0][1].text == "Все задачи"
    assert keyboard.keyboard[1][0].text == "Поиск по фильтрам"
    assert keyboard.keyboard[2][0].text == "Назад в меню"
    
    assert keyboard.resize_keyboard is True


def test_get_cancel_keyboard():
    """Test cancel keyboard creation."""
    keyboard = Keyboards.get_cancel_keyboard()
    
    assert len(keyboard.keyboard) == 1  # 1 row
    assert len(keyboard.keyboard[0]) == 1  # 1 button
    assert keyboard.keyboard[0][0].text == "Отмена"
    assert keyboard.resize_keyboard is True


def test_get_task_filters_keyboard():
    """Test task filters keyboard creation."""
    keyboard = Keyboards.get_task_filters_keyboard()
    
    # Check that it's an inline keyboard
    assert keyboard.inline_keyboard is not None
    
    # Count total buttons
    total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
    assert total_buttons >= 10  # Should have at least 10 buttons
    
    # Check for specific buttons
    button_texts = []
    for row in keyboard.inline_keyboard:
        for button in row:
            button_texts.append(button.text)
    
    assert "To Do" in button_texts
    assert "In Progress" in button_texts
    assert "Done" in button_texts
    assert "Низкий" in button_texts
    assert "Средний" in button_texts
    assert "Высокий" in button_texts
    assert "Срочный" in button_texts
    assert "Мои задачи" in button_texts
    assert "Сегодня" in button_texts
    assert "Очистить" in button_texts
    assert "Применить" in button_texts


def test_get_priority_keyboard():
    """Test priority keyboard creation."""
    keyboard = Keyboards.get_priority_keyboard()
    
    assert len(keyboard.inline_keyboard) == 2  # 2 rows
    assert len(keyboard.inline_keyboard[0]) == 2  # 2 buttons in first row
    assert len(keyboard.inline_keyboard[1]) == 2  # 2 buttons in second row
    
    button_texts = []
    for row in keyboard.inline_keyboard:
        for button in row:
            button_texts.append(button.text)
    
    assert "Низкий" in button_texts
    assert "Средний" in button_texts
    assert "Высокий" in button_texts
    assert "Срочный" in button_texts
    
    # Check callback data
    for row in keyboard.inline_keyboard:
        for button in row:
            assert button.callback_data.startswith("priority:")


def test_get_status_keyboard_without_task_id():
    """Test status keyboard creation without task ID."""
    keyboard = Keyboards.get_status_keyboard()
    
    assert len(keyboard.inline_keyboard) == 1  # 1 row
    assert len(keyboard.inline_keyboard[0]) == 3  # 3 buttons
    
    button_texts = [button.text for button in keyboard.inline_keyboard[0]]
    assert "To Do" in button_texts
    assert "In Progress" in button_texts
    assert "Done" in button_texts
    
    # Check callback data
    for button in keyboard.inline_keyboard[0]:
        assert button.callback_data.startswith("status:")


def test_get_status_keyboard_with_task_id():
    """Test status keyboard creation with task ID."""
    task_id = 123
    keyboard = Keyboards.get_status_keyboard(task_id)
    
    assert len(keyboard.inline_keyboard) == 1  # 1 row
    assert len(keyboard.inline_keyboard[0]) == 3  # 3 buttons
    
    # Check callback data includes task ID
    for button in keyboard.inline_keyboard[0]:
        assert button.callback_data.startswith(f"status_{task_id}:")


def test_get_analysis_period_keyboard():
    """Test analysis period keyboard creation."""
    keyboard = Keyboards.get_analysis_period_keyboard()
    
    assert len(keyboard.inline_keyboard) == 1  # 1 row
    assert len(keyboard.inline_keyboard[0]) == 3  # 3 buttons
    
    button_texts = [button.text for button in keyboard.inline_keyboard[0]]
    assert "Неделя" in button_texts
    assert "Месяц" in button_texts
    assert "Квартал" in button_texts
    
    # Check callback data
    for button in keyboard.inline_keyboard[0]:
        assert button.callback_data.startswith("analysis_period:")


def test_get_export_format_keyboard():
    """Test export format keyboard creation."""
    keyboard = Keyboards.get_export_format_keyboard()
    
    assert len(keyboard.inline_keyboard) == 1  # 1 row
    assert len(keyboard.inline_keyboard[0]) == 2  # 2 buttons
    
    button_texts = [button.text for button in keyboard.inline_keyboard[0]]
    assert "CSV" in button_texts
    assert "Excel" in button_texts
    
    # Check callback data
    for button in keyboard.inline_keyboard[0]:
        assert button.callback_data.startswith("export_format:")


def test_get_task_actions_keyboard():
    """Test task actions keyboard creation."""
    task_id = 456
    keyboard = Keyboards.get_task_actions_keyboard(task_id)
    
    # Should have 3 rows (2+2+1)
    assert len(keyboard.inline_keyboard) == 3
    
    # Count total buttons
    total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
    assert total_buttons == 5
    
    # Check button texts
    button_texts = []
    for row in keyboard.inline_keyboard:
        for button in row:
            button_texts.append(button.text)
    
    assert "Редактировать" in button_texts
    assert "Изменить статус" in button_texts
    assert "Изменить дедлайн" in button_texts
    assert "Переназначить" in button_texts
    assert "Удалить" in button_texts
    
    # Check callback data includes task ID
    for row in keyboard.inline_keyboard:
        for button in row:
            assert str(task_id) in button.callback_data