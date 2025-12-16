"""
Callback handlers for Telegram bot.
"""

import logging
from datetime import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from modules.api_client import APIClient
from modules.session_manager import user_sessions
from modules.keyboards import Keyboards
from modules.utils import load_and_show_tasks, convert_to_excel, csv_to_excel

logger = logging.getLogger(__name__)


async def handle_export_all_tasks(callback: types.CallbackQuery):
    """
    Handler for export all tasks callback.
    
    @param callback: CallbackQuery object
    """
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await callback.answer("Вы не авторизованы")
        return
    
    await callback.message.edit_text(
        "Экспорт всех задач\n\n"
        "Выберите формат экспорта:",
        reply_markup=Keyboards.get_export_format_keyboard()
    )
    await callback.answer()


async def handle_export_format(callback: types.CallbackQuery, state: FSMContext):
    """
    Handler for export format selection callback.
    
    @param callback: CallbackQuery object
    @param state: FSM context
    """
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await callback.answer("Вы не авторизованы")
        return
    
    _, export_format = callback.data.split(":", 1)
    
    await callback.message.edit_text(
        f"Экспорт задач в {export_format.upper()}\n\n"
        "Подготавливаю файл...",
    )
    
    async with APIClient() as api_client:
        # Get all tasks
        tasks = await api_client.get_tasks(token, {})
        
        if not tasks:
            await callback.message.edit_text(
                "Задачи не найдены для экспорта.",
            )
            await callback.answer("Нет задач для экспорта")
            return
        
        if export_format == "csv":
            # Use API for CSV export
            csv_data = await api_client.export_tasks_csv(token)
            
            if csv_data:
                # Send CSV file
                await callback.message.answer_document(
                    types.BufferedInputFile(
                        csv_data,
                        filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    ),
                    caption="Экспорт завершен\n\nФайл с задачами в CSV формате готов.",
                )
                await callback.answer("Экспорт CSV завершен")
            else:
                await callback.message.edit_text(
                    "Ошибка экспорта\n\n"
                    "Не удалось экспортировать задачи в CSV. Попробуйте позже.",
                )
                await callback.answer("Ошибка экспорта")
        
        elif export_format == "excel":
            try:
                # Try to create Excel directly from data
                excel_buffer = convert_to_excel(tasks)
                
                if excel_buffer:
                    # Send Excel file
                    await callback.message.answer_document(
                        types.BufferedInputFile(
                            excel_buffer.read(),
                            filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        ),
                        caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов.",
                    )
                    await callback.answer("Экспорт Excel завершен")
                else:
                    # If direct Excel creation fails, try through CSV
                    logger.info("Direct Excel creation failed, trying through CSV...")
                    
                    # First get CSV
                    csv_data = await api_client.export_tasks_csv(token)
                    
                    if csv_data:
                        # Convert CSV to Excel
                        excel_buffer = csv_to_excel(csv_data)
                        
                        if excel_buffer:
                            # Send Excel file
                            await callback.message.answer_document(
                                types.BufferedInputFile(
                                    excel_buffer.read(),
                                    filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                ),
                                caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов (создан из CSV).",
                            )
                            await callback.answer("Экспорт Excel завершен")
                        else:
                            await callback.message.edit_text(
                                "Ошибка экспорта\n\n"
                                "Не удалось создать Excel файл даже через CSV. Попробуйте экспортировать в CSV.",
                            )
                            await callback.answer("Ошибка создания Excel")
                    else:
                        await callback.message.edit_text(
                            "Ошибка экспорта\n\n"
                            "Не удалось получить данные для экспорта. Попробуйте позже.",
                        )
                        await callback.answer("Ошибка получения данных")
            except Exception as e:
                logger.error(f"Excel creation error: {e}")
                
                # Try alternative method - create CSV and convert
                try:
                    csv_data = await api_client.export_tasks_csv(token)
                    if csv_data:
                        excel_buffer = csv_to_excel(csv_data)
                        if excel_buffer:
                            await callback.message.answer_document(
                                types.BufferedInputFile(
                                    excel_buffer.read(),
                                    filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                ),
                                caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов (создан через CSV).",
                            )
                            await callback.answer("Экспорт Excel завершен")
                        else:
                            await callback.message.edit_text(
                                f"Ошибка экспорта\n\n"
                                f"Не удалось создать Excel файл: {str(e)[:100]}",
                            )
                            await callback.answer("Ошибка экспорта")
                    else:
                        await callback.message.edit_text(
                            f"Ошибка экспорта\n\n"
                            f"Не удалось получить данные: {str(e)[:100]}",
                        )
                        await callback.answer("Ошибка экспорта")
                except Exception as e2:
                    logger.error(f"Alternative method error: {e2}")
                    await callback.message.edit_text(
                        f"Ошибка экспорта\n\n"
                        f"Не удалось создать Excel файл. Попробуйте экспортировать в CSV.",
                    )
                    await callback.answer("Ошибка экспорта")


async def handle_task_filters(callback: types.CallbackQuery, state: FSMContext):
    """
    Handler for task filters callback.
    
    @param callback: CallbackQuery object
    @param state: FSM context
    """
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await callback.answer("Вы не авторизованы")
        return
    
    filter_type, filter_value = callback.data.split(":", 1)
    current_filters = await state.get_data() or {}
    
    if filter_type == "filter_status":
        status_filters = current_filters.get('status', [])
        if filter_value in status_filters:
            status_filters.remove(filter_value)
            await callback.answer(f"Фильтр {filter_value} удален")
        else:
            status_filters.append(filter_value)
            await callback.answer(f"Фильтр {filter_value} добавлен")
        current_filters['status'] = status_filters
    
    elif filter_type == "filter_priority":
        priority_filters = current_filters.get('priority', [])
        if filter_value in priority_filters:
            priority_filters.remove(filter_value)
            await callback.answer(f"Фильтр {filter_value} удален")
        else:
            priority_filters.append(filter_value)
            await callback.answer(f"Фильтр {filter_value} добавлен")
        current_filters['priority'] = priority_filters
    
    elif filter_type == "filter_assignee":
        if filter_value == "me":
            user_info = user_sessions.get_user_info(user_id)
            if user_info:
                user_data = user_info.get('user', {})
                username = user_data.get('telegram_username')
                if username:
                    current_filters['assignee'] = username
                    await callback.answer("Показать только мои задачи")
        else:
            current_filters.pop('assignee', None)
            await callback.answer("Фильтр назначения сброшен")
    
    elif filter_type == "filter_today":
        if filter_value == "true":
            today = datetime.now().strftime('%Y-%m-%d')
            current_filters['date_from'] = today
            current_filters['date_to'] = today
            await callback.answer("Показать задачи на сегодня")
    
    elif filter_type == "filter_clear":
        await state.clear()
        current_filters = {}
        await callback.message.edit_text(
            "Фильтры сброшены\n\n"
            "Выберите фильтры для отображения задач:",
            reply_markup=Keyboards.get_task_filters_keyboard()
        )
        await callback.answer("Фильтры сброшены")
        return
    
    elif filter_type == "filter_apply":
        # Apply filters and load tasks
        await load_and_show_tasks(callback.message, token, current_filters, "отфильтрованные задачи")
        await callback.answer("Фильтры применены")
        return
    
    await state.set_data(current_filters)
    
    filter_text = "Текущие фильтры:\n"
    if current_filters.get('status'):
        filter_text += f"Статус: {', '.join(current_filters['status'])}\n"
    if current_filters.get('priority'):
        filter_text += f"Приоритет: {', '.join(current_filters['priority'])}\n"
    if current_filters.get('assignee'):
        filter_text += f"Назначена: {current_filters['assignee']}\n"
    if current_filters.get('date_from'):
        filter_text += f"Дата: {current_filters['date_from']}"
        if current_filters.get('date_to'):
            filter_text += f" - {current_filters['date_to']}"
        filter_text += "\n"
    
    if not current_filters:
        filter_text = "Фильтры задач\n\nВыберите фильтры для отображения задач:"
    
    await callback.message.edit_text(
        filter_text,
        reply_markup=Keyboards.get_task_filters_keyboard()
    )


async def handle_analysis_period(callback: types.CallbackQuery):
    """
    Handler for analysis period selection callback.
    
    @param callback: CallbackQuery object
    """
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)
    
    if not token:
        await callback.answer("Вы не авторизованы")
        return
    
    _, period = callback.data.split(":", 1)
    
    period_display = {
        'last_week': 'неделю',
        'last_month': 'месяц',
        'last_quarter': 'квартал'
    }.get(period, period)
    
    await callback.message.edit_text(
        f"Анализ задач за {period_display}\n\n"
        "Запрашиваю анализ у AI...",
    )
    
    async with APIClient() as api_client:
        analysis_params = {
            'time_period': period,
            'metrics': ['productivity', 'bottlenecks', 'team_performance'],
            'include_recommendations': True
        }
        
        analysis_result = await api_client.get_llm_analysis(token, analysis_params)
        
        if analysis_result:
            summary = analysis_result.get('analysis', {}).get('summary', {})
            recommendations = analysis_result.get('recommendations', [])
            
            analysis_text = (
                f"AI Анализ задач ({period_display})\n\n"
                f"Общая статистика:\n"
                f"- Всего задач: {summary.get('total_tasks', 0)}\n"
                f"- Выполнено: {summary.get('completed', 0)}\n"
                f"- В работе: {summary.get('in_progress', 0)}\n"
                f"- Просрочено: {summary.get('overdue', 0)}\n"
                f"- Процент выполнения: {summary.get('completion_rate', '0%')}\n\n"
            )
            
            if recommendations:
                analysis_text += "Рекомендации:\n"
                for i, rec in enumerate(recommendations[:5], 1):
                    analysis_text += f"{i}. {rec}\n"
            
            await callback.message.edit_text(
                analysis_text,
            )
        else:
            await callback.message.edit_text(
                "Ошибка анализа\n\n"
                "Не удалось получить анализ задач. Попробуйте позже.",
            )
    
    await callback.answer("Анализ завершен")