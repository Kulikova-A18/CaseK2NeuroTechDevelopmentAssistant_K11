"""
Utility functions and helpers.
Contains common utilities used across the system.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

import logging

from modules.constants import SystemConstants

def generate_dates():
    base_date = datetime.now()
    created_dates = []
    due_dates = []

    for i in range(40):
        created_date = base_date - timedelta(days=40-i)
        due_date = created_date + timedelta(days=7 + i % 14)
        created_dates.append(created_date.strftime('%Y-%m-%d'))
        due_dates.append(due_date.strftime('%Y-%m-%d'))

    return created_dates, due_dates

def initialize_sample_data(tasks_manager, users_manager):
    """
    Initialize sample system data.
    Creates example users and tasks for demonstration.
    
    @param tasks_manager: CSV data manager for tasks
    @param users_manager: CSV data manager for users
    """
    # Check if data already exists
    existing_users = users_manager.read_all()
    if len(existing_users) > 1:  # Account for header
        logging.info("Sample data already exists")
        return
    
    logging.info("Initializing sample data...")
    
    # Create sample users
    sample_users = [
        {
            'telegram_username': '@admin_ivan',
            'full_name': 'Иван Петров',
            'role': 'admin',
            'is_active': 'True',
            'email': 'ivan@company.com',
            'department': 'IT'
        },
        {
            'telegram_username': '@manager_anna',
            'full_name': 'Анна Сидорова',
            'role': 'manager',
            'is_active': 'True',
            'email': 'anna@company.com',
            'department': 'Project Management'
        },
        {
            'telegram_username': '@developer_alex',
            'full_name': 'Алексей Козлов',
            'role': 'member',
            'is_active': 'True',
            'email': 'alex@company.com',
            'department': 'Development'
        },
        {
            'telegram_username': '@viewer_olga',
            'full_name': 'Ольга Новикова',
            'role': 'viewer',
            'is_active': 'True',
            'email': 'olga@company.com',
            'department': 'Sales'
        },
        {
            'telegram_username': '@developer_maria',
            'full_name': 'Мария Семенова',
            'role': 'member',
            'is_active': 'True',
            'email': 'maria@company.com',
            'department': 'Development'
        },
        {
            'telegram_username': '@analyst_dmitry',
            'full_name': 'Дмитрий Волков',
            'role': 'member',
            'is_active': 'True',
            'email': 'dmitry@company.com',
            'department': 'Analytics'
        },
        {
            'telegram_username': '@manager_pavel',
            'full_name': 'Павел Орлов',
            'role': 'manager',
            'is_active': 'True',
            'email': 'pavel@company.com',
            'department': 'Project Management'
        },
        {
            'telegram_username': '@hr_elena',
            'full_name': 'Елена Ковалева',
            'role': 'admin',
            'is_active': 'True',
            'email': 'elena@company.com',
            'department': 'HR'
        },
        {
            'telegram_username': '@sales_igor',
            'full_name': 'Игорь Баранов',
            'role': 'member',
            'is_active': 'True',
            'email': 'igor@company.com',
            'department': 'Sales'
        },
        {
            'telegram_username': '@viewer_tatiana',
            'full_name': 'Татьяна Морозова',
            'role': 'viewer',
            'is_active': 'True',
            'email': 'tatiana@company.com',
            'department': 'Marketing'
        },
        {
            'telegram_username': '@devops_sergey',
            'full_name': 'Сергей Павлов',
            'role': 'member',
            'is_active': 'True',
            'email': 'sergey@company.com',
            'department': 'DevOps'
        },
        {
            'telegram_username': '@qa_ekaterina',
            'full_name': 'Екатерина Федорова',
            'role': 'member',
            'is_active': 'True',
            'email': 'ekaterina@company.com',
            'department': 'QA'
        },
        {
            'telegram_username': '@designer_nikolay',
            'full_name': 'Николай Соколов',
            'role': 'member',
            'is_active': 'True',
            'email': 'nikolay@company.com',
            'department': 'Design'
        },
        {
            'telegram_username': '@support_andrey',
            'full_name': 'Андрей Лебедев',
            'role': 'member',
            'is_active': 'True',
            'email': 'andrey@company.com',
            'department': 'Support'
        },
        {
            'telegram_username': '@finance_svetlana',
            'full_name': 'Светлана Зайцева',
            'role': 'viewer',
            'is_active': 'True',
            'email': 'svetlana@company.com',
            'department': 'Finance'
        },
        {
            'telegram_username': '@pm_roman',
            'full_name': 'Роман Егоров',
            'role': 'manager',
            'is_active': 'True',
            'email': 'roman@company.com',
            'department': 'Product Management'
        },
        {
            'telegram_username': '@marketing_irina',
            'full_name': 'Ирина Степанова',
            'role': 'member',
            'is_active': 'True',
            'email': 'irina@company.com',
            'department': 'Marketing'
        },
        {
            'telegram_username': '@data_mikhail',
            'full_name': 'Михаил Попов',
            'role': 'member',
            'is_active': 'True',
            'email': 'mikhail@company.com',
            'department': 'Data Science'
        },
        {
            'telegram_username': '@inactive_vladimir',
            'full_name': 'Владимир Васильев',
            'role': 'viewer',
            'is_active': 'False',
            'email': 'vladimir@company.com',
            'department': 'Sales'
        },
        {
            'telegram_username': '@kulikova_alyona',
            'full_name': 'Алена Куликова',
            'role': 'admin',
            'is_active': 'True',
            'email': 'alyona@company.com',
            'department': 'Administration'
        }
    ]
    
    for user_data in sample_users:
        users_manager.insert(user_data)

    created_dates, due_dates = generate_dates()

    # Create sample tasks
    sample_tasks = [
        {
            'task_id': '101',
            'title': 'Разработка REST API',
            'description': 'Создать API endpoints для системы управления задачами',
            'status': 'in_progress',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'high',
            'tags': json.dumps(['backend', 'api', 'priority'], ensure_ascii=False)
        },
        {
            'task_id': '102',
            'title': 'Исправить критический баг',
            'description': 'Ошибка при сохранении данных в CSV',
            'status': 'done',
            'assignee': '@developer_alex',
            'creator': '@admin_ivan',
            'priority': 'urgent',
            'tags': json.dumps(['bug', 'critical', 'hotfix'], ensure_ascii=False)
        },
        {
            'task_id': '103',
            'title': 'Обновить документацию',
            'description': 'Добавить новые API методы в документацию',
            'status': 'todo',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'medium',
            'tags': json.dumps(['docs', 'api'], ensure_ascii=False)
        },
        # Новые задачи (40 штук)
        {
            'task_id': '104',
            'title': 'Дизайн лендинга продукта',
            'description': 'Разработать макет главной страницы нового продукта',
            'status': 'in_progress',
            'assignee': '@designer_nikolay',
            'creator': '@pm_roman',
            'priority': 'high',
            'created_at': created_dates[0],
            'due_date': due_dates[0],
            'tags': json.dumps(['design', 'ui', 'landing'], ensure_ascii=False)
        },
        {
            'task_id': '105',
            'title': 'Настройка CI/CD пайплайна',
            'description': 'Автоматизация сборки и деплоя приложения',
            'status': 'done',
            'assignee': '@devops_sergey',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[1],
            'due_date': due_dates[1],
            'tags': json.dumps(['devops', 'ci/cd', 'automation'], ensure_ascii=False)
        },
        {
            'task_id': '106',
            'title': 'Тестирование платежного модуля',
            'description': 'Провести интеграционное тестирование платежной системы',
            'status': 'in_progress',
            'assignee': '@qa_ekaterina',
            'creator': '@manager_pavel',
            'priority': 'high',
            'created_at': created_dates[2],
            'due_date': due_dates[2],
            'tags': json.dumps(['testing', 'payment', 'integration'], ensure_ascii=False)
        },
        {
            'task_id': '107',
            'title': 'Анализ конкурентов',
            'description': 'Исследование продуктов основных конкурентов на рынке',
            'status': 'todo',
            'assignee': '@analyst_dmitry',
            'creator': '@pm_roman',
            'priority': 'medium',
            'created_at': created_dates[3],
            'due_date': due_dates[3],
            'tags': json.dumps(['research', 'analysis', 'market'], ensure_ascii=False)
        },
        {
            'task_id': '108',
            'title': 'Подготовка квартального отчета',
            'description': 'Сбор данных и подготовка отчета за 3 квартал',
            'status': 'in_progress',
            'assignee': '@finance_svetlana',
            'creator': '@hr_elena',
            'priority': 'medium',
            'created_at': created_dates[4],
            'due_date': due_dates[4],
            'tags': json.dumps(['finance', 'report', 'quarterly'], ensure_ascii=False)
        },
        {
            'task_id': '109',
            'title': 'Обновление базы данных клиентов',
            'description': 'Миграция клиентской базы на новую версию CRM',
            'status': 'todo',
            'assignee': '@sales_igor',
            'creator': '@manager_anna',
            'priority': 'low',
            'created_at': created_dates[5],
            'due_date': due_dates[5],
            'tags': json.dumps(['crm', 'migration', 'sales'], ensure_ascii=False)
        },
        {
            'task_id': '110',
            'title': 'Оптимизация скорости загрузки сайта',
            'description': 'Улучшение показателей PageSpeed Insights',
            'status': 'in_progress',
            'assignee': '@developer_maria',
            'creator': '@manager_pavel',
            'priority': 'high',
            'created_at': created_dates[6],
            'due_date': due_dates[6],
            'tags': json.dumps(['performance', 'optimization', 'frontend'], ensure_ascii=False)
        },
        {
            'task_id': '111',
            'title': 'Организация тимбилдинга',
            'description': 'Планирование корпоративного мероприятия для сотрудников',
            'status': 'todo',
            'assignee': '@hr_elena',
            'creator': '@admin_ivan',
            'priority': 'low',
            'created_at': created_dates[7],
            'due_date': due_dates[7],
            'tags': json.dumps(['hr', 'event', 'team-building'], ensure_ascii=False)
        },
        {
            'task_id': '112',
            'title': 'Разработка мобильного приложения',
            'description': 'Создание iOS и Android версии приложения',
            'status': 'in_progress',
            'assignee': '@developer_alex',
            'creator': '@pm_roman',
            'priority': 'high',
            'created_at': created_dates[8],
            'due_date': due_dates[8],
            'tags': json.dumps(['mobile', 'ios', 'android', 'development'], ensure_ascii=False)
        },
        {
            'task_id': '113',
            'title': 'Кампания в социальных сетях',
            'description': 'Запуск рекламной кампании в Facebook и Instagram',
            'status': 'done',
            'assignee': '@marketing_irina',
            'creator': '@manager_anna',
            'priority': 'medium',
            'created_at': created_dates[9],
            'due_date': due_dates[9],
            'tags': json.dumps(['marketing', 'social', 'campaign'], ensure_ascii=False)
        },
        {
            'task_id': '114',
            'title': 'Обучение новых сотрудников',
            'description': 'Проведение онбординга для новых разработчиков',
            'status': 'in_progress',
            'assignee': '@developer_maria',
            'creator': '@hr_elena',
            'priority': 'medium',
            'created_at': created_dates[10],
            'due_date': due_dates[10],
            'tags': json.dumps(['training', 'onboarding', 'education'], ensure_ascii=False)
        },
        {
            'task_id': '115',
            'title': 'Рефакторинг legacy кода',
            'description': 'Улучшение старого кода основной кодовой базы',
            'status': 'todo',
            'assignee': '@developer_alex',
            'creator': '@manager_pavel',
            'priority': 'medium',
            'created_at': created_dates[11],
            'due_date': due_dates[11],
            'tags': json.dumps(['refactoring', 'legacy', 'code-quality'], ensure_ascii=False)
        },
        {
            'task_id': '116',
            'title': 'Мониторинг серверов',
            'description': 'Настройка системы мониторинга и алертов',
            'status': 'done',
            'assignee': '@devops_sergey',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[12],
            'due_date': due_dates[12],
            'tags': json.dumps(['monitoring', 'servers', 'devops'], ensure_ascii=False)
        },
        {
            'task_id': '117',
            'title': 'Анализ пользовательского поведения',
            'description': 'Исследование метрик пользовательского взаимодействия',
            'status': 'in_progress',
            'assignee': '@data_mikhail',
            'creator': '@analyst_dmitry',
            'priority': 'medium',
            'created_at': created_dates[13],
            'due_date': due_dates[13],
            'tags': json.dumps(['analytics', 'user-behavior', 'data'], ensure_ascii=False)
        },
        {
            'task_id': '118',
            'title': 'Поддержка пользователей',
            'description': 'Обработка обращений в службу поддержки',
            'status': 'in_progress',
            'assignee': '@support_andrey',
            'creator': '@manager_anna',
            'priority': 'medium',
            'created_at': created_dates[14],
            'due_date': due_dates[14],
            'tags': json.dumps(['support', 'helpdesk', 'users'], ensure_ascii=False)
        },
        {
            'task_id': '119',
            'title': 'Презентация для инвесторов',
            'description': 'Подготовка инвестиционного питча',
            'status': 'todo',
            'assignee': '@pm_roman',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[15],
            'due_date': due_dates[15],
            'tags': json.dumps(['presentation', 'investors', 'pitch'], ensure_ascii=False)
        },
        {
            'task_id': '120',
            'title': 'Обновление политики безопасности',
            'description': 'Пересмотр и обновление политик информационной безопасности',
            'status': 'in_progress',
            'assignee': '@admin_ivan',
            'creator': '@hr_elena',
            'priority': 'high',
            'created_at': created_dates[16],
            'due_date': due_dates[16],
            'tags': json.dumps(['security', 'policy', 'compliance'], ensure_ascii=False)
        },
        {
            'task_id': '121',
            'title': 'Тестирование новой функциональности',
            'description': 'Регрессионное тестирование после релиза',
            'status': 'done',
            'assignee': '@qa_ekaterina',
            'creator': '@developer_maria',
            'priority': 'medium',
            'created_at': created_dates[17],
            'due_date': due_dates[17],
            'tags': json.dumps(['testing', 'regression', 'release'], ensure_ascii=False)
        },
        {
            'task_id': '122',
            'title': 'Разработка системы нотификаций',
            'description': 'Создание системы email и push уведомлений',
            'status': 'in_progress',
            'assignee': '@developer_alex',
            'creator': '@manager_pavel',
            'priority': 'medium',
            'created_at': created_dates[18],
            'due_date': due_dates[18],
            'tags': json.dumps(['notifications', 'email', 'backend'], ensure_ascii=False)
        },
        {
            'task_id': '123',
            'title': 'Подбор кандидатов на позицию DevOps',
            'description': 'Поиск и интервью кандидатов на DevOps позицию',
            'status': 'todo',
            'assignee': '@hr_elena',
            'creator': '@devops_sergey',
            'priority': 'high',
            'created_at': created_dates[19],
            'due_date': due_dates[19],
            'tags': json.dumps(['recruitment', 'devops', 'hr'], ensure_ascii=False)
        },
        {
            'task_id': '124',
            'title': 'Анализ финансовых показателей',
            'description': 'Расчет ROI и других финансовых метрик',
            'status': 'in_progress',
            'assignee': '@finance_svetlana',
            'creator': '@admin_ivan',
            'priority': 'medium',
            'created_at': created_dates[20],
            'due_date': due_dates[20],
            'tags': json.dumps(['finance', 'roi', 'analysis'], ensure_ascii=False)
        },
        {
            'task_id': '125',
            'title': 'Интеграция с платежным шлюзом',
            'description': 'Подключение нового платежного провайдера',
            'status': 'todo',
            'assignee': '@developer_maria',
            'creator': '@manager_anna',
            'priority': 'high',
            'created_at': created_dates[21],
            'due_date': due_dates[21],
            'tags': json.dumps(['integration', 'payment', 'api'], ensure_ascii=False)
        },
        {
            'task_id': '126',
            'title': 'Контент для блога компании',
            'description': 'Написание статей для корпоративного блога',
            'status': 'in_progress',
            'assignee': '@marketing_irina',
            'creator': '@pm_roman',
            'priority': 'low',
            'created_at': created_dates[22],
            'due_date': due_dates[22],
            'tags': json.dumps(['content', 'blog', 'marketing'], ensure_ascii=False)
        },
        {
            'task_id': '127',
            'title': 'Резервное копирование данных',
            'description': 'Настройка автоматического бэкапа баз данных',
            'status': 'done',
            'assignee': '@devops_sergey',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[23],
            'due_date': due_dates[23],
            'tags': json.dumps(['backup', 'database', 'devops'], ensure_ascii=False)
        },
        {
            'task_id': '128',
            'title': 'А/B тестирование лендинга',
            'description': 'Тестирование двух версий посадочной страницы',
            'status': 'in_progress',
            'assignee': '@analyst_dmitry',
            'creator': '@designer_nikolay',
            'priority': 'medium',
            'created_at': created_dates[24],
            'due_date': due_dates[24],
            'tags': json.dumps(['a/b-testing', 'analytics', 'conversion'], ensure_ascii=False)
        },
        {
            'task_id': '129',
            'title': 'Обновление библиотек зависимостей',
            'description': 'Обновление версий всех npm пакетов',
            'status': 'todo',
            'assignee': '@developer_alex',
            'creator': '@manager_pavel',
            'priority': 'low',
            'created_at': created_dates[25],
            'due_date': due_dates[25],
            'tags': json.dumps(['dependencies', 'npm', 'maintenance'], ensure_ascii=False)
        },
        {
            'task_id': '130',
            'title': 'Продажи ключевым клиентам',
            'description': 'Переговоры с крупными B2B клиентами',
            'status': 'in_progress',
            'assignee': '@sales_igor',
            'creator': '@manager_anna',
            'priority': 'high',
            'created_at': created_dates[26],
            'due_date': due_dates[26],
            'tags': json.dumps(['sales', 'b2b', 'negotiation'], ensure_ascii=False)
        },
        {
            'task_id': '131',
            'title': 'Дизайн иконок приложения',
            'description': 'Создание набора иконок для UI',
            'status': 'done',
            'assignee': '@designer_nikolay',
            'creator': '@developer_maria',
            'priority': 'medium',
            'created_at': created_dates[27],
            'due_date': due_dates[27],
            'tags': json.dumps(['design', 'icons', 'ui'], ensure_ascii=False)
        },
        {
            'task_id': '132',
            'title': 'Оптимизация SQL запросов',
            'description': 'Улучшение производительности медленных запросов',
            'status': 'in_progress',
            'assignee': '@developer_maria',
            'creator': '@manager_pavel',
            'priority': 'medium',
            'created_at': created_dates[28],
            'due_date': due_dates[28],
            'tags': json.dumps(['sql', 'optimization', 'database'], ensure_ascii=False)
        },
        {
            'task_id': '133',
            'title': 'Подготовка годового отчета',
            'description': 'Сбор данных и подготовка годового отчета',
            'status': 'todo',
            'assignee': '@finance_svetlana',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[29],
            'due_date': due_dates[29],
            'tags': json.dumps(['report', 'annual', 'finance'], ensure_ascii=False)
        },
        {
            'task_id': '134',
            'title': 'Разработка дашборда аналитики',
            'description': 'Создание панели управления с ключевыми метриками',
            'status': 'in_progress',
            'assignee': '@data_mikhail',
            'creator': '@analyst_dmitry',
            'priority': 'high',
            'created_at': created_dates[30],
            'due_date': due_dates[30],
            'tags': json.dumps(['dashboard', 'analytics', 'data-visualization'], ensure_ascii=False)
        },
        {
            'task_id': '135',
            'title': 'Обновление серверного оборудования',
            'description': 'Замена устаревших серверов в дата-центре',
            'status': 'todo',
            'assignee': '@devops_sergey',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[31],
            'due_date': due_dates[31],
            'tags': json.dumps(['hardware', 'servers', 'infrastructure'], ensure_ascii=False)
        },
        {
            'task_id': '136',
            'title': 'Создание видео-туториалов',
            'description': 'Запись обучающих видео для новых пользователей',
            'status': 'in_progress',
            'assignee': '@marketing_irina',
            'creator': '@support_andrey',
            'priority': 'medium',
            'created_at': created_dates[32],
            'due_date': due_dates[32],
            'tags': json.dumps(['video', 'tutorials', 'education'], ensure_ascii=False)
        },
        {
            'task_id': '137',
            'title': 'Аудит безопасности приложения',
            'description': 'Проверка уязвимостей и безопасности кода',
            'status': 'done',
            'assignee': '@developer_alex',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[33],
            'due_date': due_dates[33],
            'tags': json.dumps(['security', 'audit', 'vulnerability'], ensure_ascii=False)
        },
        {
            'task_id': '138',
            'title': 'Планирование следующего спринта',
            'description': 'Подготовка задач и оценка времени для спринта',
            'status': 'todo',
            'assignee': '@manager_pavel',
            'creator': '@pm_roman',
            'priority': 'medium',
            'created_at': created_dates[34],
            'due_date': due_dates[34],
            'tags': json.dumps(['sprint', 'planning', 'agile'], ensure_ascii=False)
        },
        {
            'task_id': '139',
            'title': 'Тестирование на кросс-браузерность',
            'description': 'Проверка работы сайта в разных браузерах',
            'status': 'in_progress',
            'assignee': '@qa_ekaterina',
            'creator': '@designer_nikolay',
            'priority': 'medium',
            'created_at': created_dates[35],
            'due_date': due_dates[35],
            'tags': json.dumps(['testing', 'cross-browser', 'compatibility'], ensure_ascii=False)
        },
        {
            'task_id': '140',
            'title': 'Обновление лицензий ПО',
            'description': 'Продление лицензий на программное обеспечение',
            'status': 'todo',
            'assignee': '@admin_ivan',
            'creator': '@hr_elena',
            'priority': 'low',
            'created_at': created_dates[36],
            'due_date': due_dates[36],
            'tags': json.dumps(['licenses', 'software', 'legal'], ensure_ascii=False)
        },
        {
            'task_id': '141',
            'title': 'Разработка системы поиска',
            'description': 'Создание полнотекстового поиска по базе данных',
            'status': 'in_progress',
            'assignee': '@developer_maria',
            'creator': '@manager_pavel',
            'priority': 'medium',
            'created_at': created_dates[37],
            'due_date': due_dates[37],
            'tags': json.dumps(['search', 'elasticsearch', 'backend'], ensure_ascii=False)
        },
        {
            'task_id': '142',
            'title': 'Анализ рынка для нового продукта',
            'description': 'Исследование потенциального рынка для нового продукта',
            'status': 'done',
            'assignee': '@analyst_dmitry',
            'creator': '@pm_roman',
            'priority': 'high',
            'created_at': created_dates[38],
            'due_date': due_dates[38],
            'tags': json.dumps(['market-research', 'product', 'analysis'], ensure_ascii=False)
        },
        {
            'task_id': '143',
            'title': 'Настройка системы логирования',
            'description': 'Внедрение централизованной системы логов',
            'status': 'in_progress',
            'assignee': '@devops_sergey',
            'creator': '@developer_alex',
            'priority': 'medium',
            'created_at': created_dates[39],
            'due_date': due_dates[39],
            'tags': json.dumps(['logging', 'monitoring', 'devops'], ensure_ascii=False)
        },
        {
            'task_id': '201',
            'title': 'Аудит системы безопасности',
            'description': 'Полный аудит информационной безопасности компании',
            'status': 'in_progress',
            'assignee': '@kulikova_alyona',
            'creator': '@admin_ivan',
            'priority': 'urgent',
            'created_at': created_dates[3],
            'due_date': due_dates[3],
            'tags': json.dumps(['security', 'audit', 'compliance', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '202',
            'title': 'Обновление политик доступа',
            'description': 'Пересмотр и обновление политик доступа к системам',
            'status': 'todo',
            'assignee': '@kulikova_alyona',
            'creator': '@hr_elena',
            'priority': 'high',
            'created_at': created_dates[4],
            'due_date': due_dates[4],
            'tags': json.dumps(['access-control', 'policies', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '203',
            'title': 'Координация с внешними аудиторами',
            'description': 'Организация проверки внешними аудиторами',
            'status': 'in_progress',
            'assignee': '@kulikova_alyona',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[5],
            'due_date': due_dates[5],
            'tags': json.dumps(['audit', 'coordination', 'external', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '204',
            'title': 'Подготовка отчетности для руководства',
            'description': 'Анализ и подготовка отчетов по безопасности для совета директоров',
            'status': 'todo',
            'assignee': '@kulikova_alyona',
            'creator': '@hr_elena',
            'priority': 'medium',
            'created_at': created_dates[6],
            'due_date': due_dates[6],
            'tags': json.dumps(['reporting', 'management', 'security', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '205',
            'title': 'Обновление регламентов ИБ',
            'description': 'Разработка новых регламентов информационной безопасности',
            'status': 'in_progress',
            'assignee': '@kulikova_alyona',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[7],
            'due_date': due_dates[7],
            'tags': json.dumps(['regulations', 'security', 'documentation', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '206',
            'title': 'Проверка соответствия GDPR',
            'description': 'Аудит соответствия требованиям GDPR',
            'status': 'done',
            'assignee': '@kulikova_alyona',
            'creator': '@hr_elena',
            'priority': 'urgent',
            'created_at': created_dates[8],
            'due_date': due_dates[8],
            'tags': json.dumps(['gdpr', 'compliance', 'privacy', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '207',
            'title': 'Инвентаризация активов',
            'description': 'Полная инвентаризация информационных активов компании',
            'status': 'in_progress',
            'assignee': '@kulikova_alyona',
            'creator': '@admin_ivan',
            'priority': 'medium',
            'created_at': created_dates[9],
            'due_date': due_dates[9],
            'tags': json.dumps(['inventory', 'assets', 'security', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '208',
            'title': 'Обучение сотрудников безопасности',
            'description': 'Организация тренингов по информационной безопасности',
            'status': 'todo',
            'assignee': '@kulikova_alyona',
            'creator': '@hr_elena',
            'priority': 'medium',
            'created_at': created_dates[10],
            'due_date': due_dates[10],
            'tags': json.dumps(['training', 'security', 'education', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '209',
            'title': 'Анализ инцидентов безопасности',
            'description': 'Расследование и анализ последних инцидентов безопасности',
            'status': 'in_progress',
            'assignee': '@kulikova_alyona',
            'creator': '@admin_ivan',
            'priority': 'high',
            'created_at': created_dates[11],
            'due_date': due_dates[11],
            'tags': json.dumps(['incidents', 'analysis', 'security', 'admin'], ensure_ascii=False)
        },
        {
            'task_id': '210',
            'title': 'Планирование улучшений ИБ',
            'description': 'Разработка плана улучшений системы безопасности на следующий год',
            'status': 'todo',
            'assignee': '@kulikova_alyona',
            'creator': '@hr_elena',
            'priority': 'medium',
            'created_at': created_dates[12],
            'due_date': due_dates[12],
            'tags': json.dumps(['planning', 'improvements', 'security', 'admin'], ensure_ascii=False)
        }
    ]
    
    for task_data in sample_tasks:
        tasks_manager.insert(task_data)

