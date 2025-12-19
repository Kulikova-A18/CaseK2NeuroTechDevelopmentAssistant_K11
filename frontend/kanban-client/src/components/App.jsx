import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Конфигурация API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://193.233.171.205:5000' || 'http://193.233.171.205:5000';

// Конфигурация axios
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Интерсептор для добавления токена
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Интерсептор для обработки истечения токена
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
                        refresh_token: refreshToken
                    });

                    if (response.data.status === 'success') {
                        localStorage.setItem('access_token', response.data.data.access_token);
                        localStorage.setItem('refresh_token', response.data.data.refresh_token);

                        originalRequest.headers.Authorization = `Bearer ${response.data.data.access_token}`;
                        return api(originalRequest);
                    }
                }
            } catch (refreshError) {
                console.error('Ошибка обновления токена:', refreshError);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user_info');
                window.location.href = '/login';
            }
        }

        return Promise.reject(error);
    }
);

// Начальные данные доски
const initialColumns = [
    { id: 'col-1', title: 'К выполнению', color: '#00008B' },
    { id: 'col-2', title: 'В процессе', color: '#00008B' },
    { id: 'col-3', title: 'Выполнено', color: '#00008B' }
];

const priorities = [
    { value: 'low', label: 'Низкий', color: 'bg-green-100 text-green-800' },
    { value: 'medium', label: 'Средний', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'high', label: 'Высокий', color: 'bg-orange-100 text-orange-800' },
    { value: 'urgent', label: 'Критический', color: 'bg-red-100 text-red-800' }
];

const App = () => {
    // Состояние аутентификации
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);
    const [users, setUsers] = useState([]);
    const [allRegisteredUsers, setAllRegisteredUsers] = useState([]); // Все пользователи с сервера

    // Состояние доски
    const [columns, setColumns] = useState(initialColumns);
    const [tasks, setTasks] = useState([]);
    const [filteredTasks, setFilteredTasks] = useState([]);
    const [activeView, setActiveView] = useState('board');
    const [dataVersion, setDataVersion] = useState(0); // Для принудительной перезагрузки данных
    const [lastUpdateTime, setLastUpdateTime] = useState(null); // Время последнего обновления

    // Состояние документации
    const [docs, setDocs] = useState([]);
    const [selectedDoc, setSelectedDoc] = useState(null);
    const [docFolders, setDocFolders] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [isEditingDoc, setIsEditingDoc] = useState(false);
    const [expandedFolders, setExpandedFolders] = useState(new Set());

    // Состояние календаря
    const [currentDate, setCurrentDate] = useState(new Date());
    const [calendarView, setCalendarView] = useState('month');
    const [selectedCalendarTask, setSelectedCalendarTask] = useState(null);
    const [showTaskDetails, setShowTaskDetails] = useState(false);
    const [selectedTaskDetails, setSelectedTaskDetails] = useState(null);

    // Состояние профиля
    const [showProfile, setShowProfile] = useState(false);
    const [myTasksFilter, setMyTasksFilter] = useState(false);
    const [myTasks, setMyTasks] = useState([]);

    // Состояние модальных окон
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [showColumnModal, setShowColumnModal] = useState(false);
    const [showDocModal, setShowDocModal] = useState(false);
    const [showFolderModal, setShowFolderModal] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [showLLMAnalysis, setShowLLMAnalysis] = useState(false);
    const [editingTask, setEditingTask] = useState(null);
    const [editingColumn, setEditingColumn] = useState(null);
    const [editingDoc, setEditingDoc] = useState(null);
    const [selectedColumnId, setSelectedColumnId] = useState(null);

    // Состояние форм
    const [newTask, setNewTask] = useState({
        title: '',
        description: '',
        dueDate: '',
        assignee: '',
        tags: [],
        priority: 'medium',
        status: 'todo',
    });

    const [newColumn, setNewColumn] = useState({
        title: '',
        color: '#00008B'
    });

    const [newDoc, setNewDoc] = useState({
        name: '',
        content: '',
        folder: ''
    });

    const [newFolder, setNewFolder] = useState('');
    const [newTag, setNewTag] = useState('');
    const [taskFormErrors, setTaskFormErrors] = useState({});
    const [docFormErrors, setDocFormErrors] = useState({});

    // Состояние авторизации
    const [loginData, setLoginData] = useState({
        telegram_username: '',
        full_name: ''
    });

    // Состояние LLM анализа
    const [llmAnalysisData, setLlmAnalysisData] = useState({
        time_period: 'last_week',
        metrics: ['productivity', 'bottlenecks'],
        format: 'json',
        include_recommendations: true
    });

    const [analysisResult, setAnalysisResult] = useState(null);
    const [loading, setLoading] = useState(false);

    // Состояние drag and drop
    const [draggedTask, setDraggedTask] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);

    // Проверка аутентификации при загрузке
    useEffect(() => {
        checkAuth();
        loadInitialData();

        // Автоматическое обновление каждые 30 секунд
        const intervalId = setInterval(() => {
            if (isAuthenticated) {
                refreshData();
            }
        }, 30000); // 30 секунд

        return () => clearInterval(intervalId);
    }, [isAuthenticated]);

    // Загрузка данных при смене view или изменении данных
    useEffect(() => {
        if (isAuthenticated) {
            if (activeView === 'board' || activeView === 'calendar') {
                loadTasks();
                loadUsers();
                loadAllRegisteredUsers(); // Загружаем всех пользователей
            } else if (activeView === 'docs') {
                loadDocs();
            }
        }
    }, [activeView, isAuthenticated, dataVersion]);

    // Обновление фильтрованных задач при изменении фильтров
    useEffect(() => {
        if (myTasksFilter && currentUser) {
            const filtered = tasks.filter(task =>
                task.assignee === currentUser.telegram_username ||
                task.creator === currentUser.telegram_username
            );
            setMyTasks(filtered);
            setFilteredTasks(filtered);
        } else {
            setFilteredTasks(tasks);
        }
    }, [tasks, myTasksFilter, currentUser]);

    // Проверка аутентификации
    const checkAuth = () => {
        const token = localStorage.getItem('access_token');
        const userInfo = localStorage.getItem('user_info');

        if (token && userInfo) {
            setIsAuthenticated(true);
            setCurrentUser(JSON.parse(userInfo));
        } else {
            setShowLoginModal(true);
        }
    };

    // Загрузка начальных данных
    const loadInitialData = async () => {
        try {
            // Проверка здоровья системы
            await api.get('/api/health');
        } catch (error) {
            console.error('Ошибка подключения к серверу:', error);
        }
    };

    // Аутентификация
    const handleLogin = async () => {
        try {
            setLoading(true);
            const response = await api.post('/api/telegram/auth', loginData);

            if (response.data.status === 'success') {
                const { access_token, refresh_token, user } = response.data.data;

                localStorage.setItem('access_token', access_token);
                localStorage.setItem('refresh_token', refresh_token);
                localStorage.setItem('user_info', JSON.stringify(user));

                setIsAuthenticated(true);
                setCurrentUser(user);
                setShowLoginModal(false);

                // Загрузка пользователей
                await loadUsers();
                await loadAllRegisteredUsers(); // Загружаем всех пользователей
                await loadTasks(); // Загружаем задачи после авторизации
            }
        } catch (error) {
            console.error('Ошибка авторизации:', error);
            alert('Ошибка авторизации. Проверьте данные.');
        } finally {
            setLoading(false);
        }
    };

    // Выход из системы
    const handleLogout = async () => {
        try {
            await api.post('/api/auth/logout');
        } catch (error) {
            console.error('Ошибка выхода:', error);
        }

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        setIsAuthenticated(false);
        setCurrentUser(null);
        setTasks([]);
        setUsers([]);
        setAllRegisteredUsers([]);
        setDocs([]);
        setShowLoginModal(true);
        setMyTasksFilter(false);
    };

    // Загрузка пользователей (для назначения задач)
    const loadUsers = async () => {
        try {
            // В реальной системе здесь был бы эндпоинт для получения пользователей
            // Сейчас используем демо-данные
            const demoUsers = [
                { telegram_username: '@admin_ivan', full_name: 'Иван Петров', role: 'admin' },
                { telegram_username: '@manager_anna', full_name: 'Анна Сидорова', role: 'manager' },
                { telegram_username: '@developer_alex', full_name: 'Алексей Козлов', role: 'member' },
            ];
            setUsers(demoUsers);
        } catch (error) {
            console.error('Ошибка загрузки пользователей:', error);
        }
    };

    // Загрузка ВСЕХ зарегистрированных пользователей
    const loadAllRegisteredUsers = async () => {
        try {
            // В демо-режиме используем статические данные
            // В реальном приложении здесь был бы запрос к серверу /api/users
            const allUsers = [
                { telegram_username: '@admin_ivan', full_name: 'Иван Петров', role: 'admin', is_active: true },
                { telegram_username: '@manager_anna', full_name: 'Анна Сидорова', role: 'manager', is_active: true },
                { telegram_username: '@developer_alex', full_name: 'Алексей Козлов', role: 'member', is_active: true },
                { telegram_username: '@viewer_olga', full_name: 'Ольга Новикова', role: 'viewer', is_active: true },
                { telegram_username: '@designer_mike', full_name: 'Михаил Соколов', role: 'member', is_active: true },
                { telegram_username: '@qa_svetlana', full_name: 'Светлана Морозова', role: 'member', is_active: true },
            ];
            setAllRegisteredUsers(allUsers);
        } catch (error) {
            console.error('Ошибка загрузки всех пользователей:', error);
        }
    };

    // Загрузка задач - ОБНОВЛЕННАЯ ВЕРСИЯ С КЭШИРОВАНИЕМ
    const loadTasks = useCallback(async () => {
        try {
            console.log('Загрузка задач с сервера...');
            const response = await api.get('/api/tasks');
            if (response.data.status === 'success') {
                // Преобразование данных сервера в формат клиента
                const serverTasks = response.data.data.tasks.map(task => ({
                    id: `task-${task.task_id}`,
                    title: task.title,
                    description: task.description || '',
                    dueDate: task.due_date || '',
                    assignee: task.assignee || '',
                    tags: task.tags || [],
                    priority: task.priority || 'medium',
                    status: task.status || 'todo',
                    columnId: task.status === 'done' ? 'col-3' :
                        task.status === 'in_progress' ? 'col-2' : 'col-1',
                    creator: task.creator || '',
                    created_at: task.created_at,
                    updated_at: task.updated_at,
                    assignee_name: task.assignee_name || '',
                    creator_name: task.creator_name || '',
                    task_id: task.task_id // Сохраняем оригинальный ID для API
                }));

                // Сравниваем с текущими задачами
                const hasChanges = JSON.stringify(tasks) !== JSON.stringify(serverTasks);

                if (hasChanges) {
                    console.log('Обнаружены изменения в задачах. Обновляю...');
                    setTasks(serverTasks);
                    setLastUpdateTime(new Date());

                    // Фильтрация будет применена в useEffect
                    if (myTasksFilter && currentUser) {
                        const filtered = serverTasks.filter(task =>
                            task.assignee === currentUser.telegram_username ||
                            task.creator === currentUser.telegram_username
                        );
                        setMyTasks(filtered);
                        setFilteredTasks(filtered);
                    } else {
                        setFilteredTasks(serverTasks);
                    }

                    console.log(`Загружено ${serverTasks.length} задач`);
                } else {
                    console.log('Изменений в задачах нет');
                }
            }
        } catch (error) {
            console.error('Ошибка загрузки задач:', error);
            // Показываем уведомление только при первой ошибке
            if (tasks.length === 0) {
                console.log('Использую демо-данные для задач');
                // Демо-данные для первоначального отображения
                const demoTasks = [
                    {
                        id: 'task-101',
                        title: 'Разработка REST API',
                        description: 'Создать API endpoints для системы управления задачами',
                        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        assignee: '@developer_alex',
                        tags: ['backend', 'api'],
                        priority: 'high',
                        status: 'in_progress',
                        columnId: 'col-2',
                        creator: '@manager_anna',
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                        task_id: 101
                    },
                    {
                        id: 'task-102',
                        title: 'Исправить критический баг',
                        description: 'Ошибка при сохранении данных в CSV',
                        dueDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        assignee: '@developer_alex',
                        tags: ['bug', 'critical'],
                        priority: 'urgent',
                        status: 'done',
                        columnId: 'col-3',
                        creator: '@admin_ivan',
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                        task_id: 102
                    }
                ];
                setTasks(demoTasks);
                setFilteredTasks(demoTasks);
            }
        }
    }, [tasks, myTasksFilter, currentUser]);

    // Функция для принудительной перезагрузки данных
    const refreshData = useCallback(async () => {
        console.log('Принудительное обновление данных...');
        setDataVersion(prev => prev + 1);
        await loadTasks();
    }, [loadTasks]);

    // Загрузка документов
    const loadDocs = async () => {
        try {
            // В демо-режиме используем статические данные
            const demoDocs = [
                { id: 'doc-1', name: 'Начало работы.md', content: '# Добро пожаловать в проект\n\nЭто ваше руководство по началу работы.', folder: 'Руководства', lastModified: new Date() },
                { id: 'doc-2', name: 'Документация API.md', content: '# Справочник по API\n\n## Конечные точки\n\n- `/api/tasks` - Получить все задачи', folder: 'Техническая', lastModified: new Date() }
            ];
            setDocs(demoDocs);

            // Получение уникальных папок
            const folders = [...new Set(demoDocs.map(doc => doc.folder))];
            setDocFolders(folders);
            setExpandedFolders(new Set(folders));
        } catch (error) {
            console.error('Ошибка загрузки документов:', error);
        }
    };

    // Экспорт задач
    const handleExportTasks = async () => {
        try {
            const response = await api.get('/api/export/tasks.csv', {
                params: {
                    format: 'full',
                    time_period: 'all',
                    include_users: 'true'
                },
                responseType: 'blob'
            });

            // Создание ссылки для скачивания
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `tasks_export_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Ошибка экспорта:', error);
            alert('Ошибка при экспорте задач');
        }
    };

    // LLM анализ задач
    const handleLLMAnalysis = async () => {
        try {
            setLoading(true);
            const response = await api.post('/api/llm/analyze/tasks', llmAnalysisData);

            if (response.data.status === 'success') {
                setAnalysisResult(response.data.data);
                setShowLLMAnalysis(true);
            }
        } catch (error) {
            console.error('Ошибка LLM анализа:', error);
            alert('Ошибка при выполнении анализа');
        } finally {
            setLoading(false);
        }
    };

    // Изменение статуса задачи вручную
    const handleStatusChange = async (taskId, newStatus) => {
        try {
            const originalTaskId = taskId.replace('task-', '');

            // Обновление задачи на сервере
            const response = await api.put(`/api/tasks/${originalTaskId}`, {
                status: newStatus
            });

            if (response.data.status === 'success') {
                // ОБНОВЛЕНИЕ: После успешного обновления на сервере загружаем свежие данные
                await refreshData();

                alert('Статус задачи обновлен!');
            }
        } catch (error) {
            console.error('Ошибка обновления статуса задачи:', error);
            alert('Ошибка при обновлении статуса задачи');
        }
    };

    // Получение задач для даты (для календаря)
    const getTasksForDate = (date) => {
        if (!date) return [];

        const targetDate = new Date(date);
        targetDate.setHours(0, 0, 0, 0);

        return tasks.filter(task => {
            if (!task.dueDate) return false;
            const taskDate = new Date(task.dueDate);
            taskDate.setHours(0, 0, 0, 0);
            return taskDate.getTime() === targetDate.getTime();
        });
    };

    // Переключение фильтра "Мои задачи"
    const toggleMyTasksFilter = () => {
        setMyTasksFilter(!myTasksFilter);
    };

    // Построение дерева документов
    const buildDocumentTree = () => {
        const tree = {};
        docFolders.forEach(folder => {
            tree[folder] = [];
        });

        docs.forEach(doc => {
            if (!tree[doc.folder]) {
                tree[doc.folder] = [];
            }
            tree[doc.folder].push(doc);
        });

        return tree;
    };

    const documentTree = buildDocumentTree();

    // Фильтрация документов по поиску
    const filteredDocs = docs.filter(doc =>
        doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.folder.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Переключение раскрытия папки
    const toggleFolder = (folderName) => {
        const newExpanded = new Set(expandedFolders);
        if (newExpanded.has(folderName)) {
            newExpanded.delete(folderName);
        } else {
            newExpanded.add(folderName);
        }
        setExpandedFolders(newExpanded);
    };

    // Проверка, является ли задача срочной
    const isTaskUrgent = (task) => {
        if (!task.dueDate) return false;
        const dueDate = new Date(task.dueDate);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        dueDate.setHours(0, 0, 0, 0);
        return dueDate <= today;
    };

    // Drag and Drop обработчики
    const handleTaskDragStart = (e, task) => {
        e.dataTransfer.setData('text/plain', task.id);
        setDraggedTask(task);
    };

    const handleColumnDragOver = (e, columnId) => {
        e.preventDefault();
        setDragOverColumn(columnId);
    };

    const handleColumnDragLeave = () => {
        setDragOverColumn(null);
    };

    const handleColumnDrop = async (e, columnId) => {
        e.preventDefault();
        if (!draggedTask) return;

        // Определение нового статуса на основе колонки
        let newStatus = 'todo';
        if (columnId === 'col-2') newStatus = 'in_progress';
        if (columnId === 'col-3') newStatus = 'done';

        try {
            // Обновление задачи на сервере
            const taskId = draggedTask.id.replace('task-', '');
            const response = await api.put(`/api/tasks/${taskId}`, {
                status: newStatus
            });

            if (response.data.status === 'success') {
                // ОБНОВЛЕНИЕ: После успешного обновления загружаем свежие данные
                await refreshData();
            }
        } catch (error) {
            console.error('Ошибка обновления задачи:', error);
            alert('Ошибка при перемещении задачи');
        } finally {
            setDraggedTask(null);
            setDragOverColumn(null);
        }
    };

    // Показать детали задачи (для календаря)
    const showTaskDetailModal = (task) => {
        setSelectedTaskDetails(task);
        setShowTaskDetails(true);
    };

    // Валидация форм
    const validateTaskForm = (taskData) => {
        const errors = {};
        if (!taskData.title?.trim()) {
            errors.title = 'Название обязательно';
        }
        if (!taskData.dueDate) {
            errors.dueDate = 'Срок выполнения обязателен';
        }
        if (!taskData.assignee) {
            errors.assignee = 'Исполнитель обязателен';
        }
        return errors;
    };

    // Создание задачи - ОБНОВЛЕННАЯ ВЕРСИЯ
    const createTask = async () => {
        if (!selectedColumnId) return;

        const taskData = { ...newTask };
        const errors = validateTaskForm(taskData);

        if (Object.keys(errors).length > 0) {
            setTaskFormErrors(errors);
            return;
        }

        try {
            // Определение статуса на основе выбранной колонки
            let status = 'todo';
            if (selectedColumnId === 'col-2') status = 'in_progress';
            if (selectedColumnId === 'col-3') status = 'done';

            const response = await api.post('/api/tasks', {
                title: taskData.title,
                description: taskData.description,
                status: status,
                assignee: taskData.assignee,
                priority: taskData.priority,
                due_date: taskData.dueDate,
                tags: taskData.tags
            });

            if (response.data.status === 'success') {
                // ОБНОВЛЕНИЕ: После успешного создания загружаем свежие данные
                await refreshData();

                resetTaskForm();
                setShowTaskModal(false);
                setSelectedColumnId(null);

                alert('Задача успешно создана!');
            }
        } catch (error) {
            console.error('Ошибка создания задачи:', error);
            alert('Ошибка при создании задачи');
        }
    };

    // Обновление задачи - ОБНОВЛЕННАЯ ВЕРСИЯ
    const updateTask = async () => {
        const errors = validateTaskForm(editingTask);

        if (Object.keys(errors).length > 0) {
            setTaskFormErrors(errors);
            return;
        }

        try {
            const response = await api.put(`/api/tasks/${editingTask.id.replace('task-', '')}`, {
                title: editingTask.title,
                description: editingTask.description,
                status: editingTask.status,
                assignee: editingTask.assignee,
                priority: editingTask.priority,
                due_date: editingTask.dueDate,
                tags: editingTask.tags
            });

            if (response.data.status === 'success') {
                // ОБНОВЛЕНИЕ: После успешного обновления загружаем свежие данные
                await refreshData();

                setEditingTask(null);
                setShowTaskModal(false);
                setTaskFormErrors({});

                alert('Задача успешно обновлена!');
            }
        } catch (error) {
            console.error('Ошибка обновления задачи:', error);
            alert('Ошибка при обновлении задачи');
        }
    };

    // Удаление задачи - ОБНОВЛЕННАЯ ВЕРСИЯ
    const deleteTask = async (taskId) => {
        if (!window.confirm('Вы уверены, что хотите удалить эту задачу?')) {
            return;
        }

        try {
            const response = await api.delete(`/api/tasks/${taskId.replace('task-', '')}`);

            if (response.data.status === 'success') {
                // ОБНОВЛЕНИЕ: После успешного удаления загружаем свежие данные
                await refreshData();

                if (selectedCalendarTask?.id === taskId) {
                    setSelectedCalendarTask(null);
                }
                if (selectedTaskDetails?.id === taskId) {
                    setShowTaskDetails(false);
                    setSelectedTaskDetails(null);
                }

                alert('Задача успешно удалена!');
            }
        } catch (error) {
            console.error('Ошибка удаления задачи:', error);
            alert('Ошибка при удалении задачи');
        }
    };

    // Сброс формы задачи
    const resetTaskForm = () => {
        setNewTask({
            title: '',
            description: '',
            dueDate: '',
            assignee: '',
            tags: [],
            priority: 'medium',
            status: 'todo',
        });
        setNewTag('');
        setTaskFormErrors({});
    };

    // Создание документа
    const createDoc = () => {
        const errors = validateDocForm(newDoc);

        if (Object.keys(errors).length > 0) {
            setDocFormErrors(errors);
            return;
        }

        const doc = {
            id: `doc-${Date.now()}`,
            ...newDoc,
            lastModified: new Date()
        };

        setDocs([...docs, doc]);

        if (!docFolders.includes(newDoc.folder)) {
            setDocFolders(prev => [...prev, newDoc.folder]);
            setExpandedFolders(prev => new Set([...prev, newDoc.folder]));
        }

        setNewDoc({ name: '', content: '', folder: docFolders[0] || 'Руководства' });
        setDocFormErrors({});
        setShowDocModal(false);
    };

    // Обновление документа
    const updateDoc = () => {
        const updatedDocs = docs.map(doc =>
            doc.id === editingDoc.id
                ? { ...editingDoc, lastModified: new Date() }
                : doc
        );
        setDocs(updatedDocs);
        setEditingDoc(null);
        setIsEditingDoc(false);
    };

    // Валидация формы документа
    const validateDocForm = (docData) => {
        const errors = {};
        if (!docData.name?.trim()) {
            errors.name = 'Имя документа обязательно';
        }
        return errors;
    };

    // Создание папки
    const createFolder = () => {
        if (!newFolder.trim()) return;
        if (docFolders.includes(newFolder.trim())) return;

        setDocFolders(prev => [...prev, newFolder.trim()]);
        setNewFolder('');
        setShowFolderModal(false);
    };

    // Рендеринг Markdown
    const renderMarkdown = (content) => {
        if (!content) return '';
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/_(.*?)_/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/^- (.*$)/gm, '<li>$1</li>')
            .replace(/<\/li><li>/g, '</li>\n<li>')
            .replace(/^(?!<li>)(.*$)/gm, '<p>$1</p>')
            .replace(/<li>(.*?)<\/li>/g, '<ul><li>$1</li></ul>')
            .replace(/<\/ul><ul>/g, '');
    };

    // Получение дней месяца для календаря
    const getDaysInMonth = (date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const days = [];

        for (let i = 0; i < firstDay.getDay(); i++) {
            days.push(null);
        }

        for (let day = 1; day <= lastDay.getDate(); day++) {
            days.push(new Date(year, month, day));
        }

        return days;
    };

    const days = getDaysInMonth(currentDate);
    const today = new Date();

    // Получение задач для дня (улучшенная версия)
    const getTasksForDay = (date) => {
        if (!date) return [];
        return tasks.filter(task => {
            if (!task.dueDate) return false;
            const taskDate = new Date(task.dueDate);
            return taskDate.toDateString() === date.toDateString();
        });
    };

    // Рендеринг модалки авторизации
    const renderLoginModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">Вход в систему</h3>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Telegram username <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={loginData.telegram_username}
                            onChange={(e) => setLoginData({ ...loginData, telegram_username: e.target.value })}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="@username"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Полное имя
                        </label>
                        <input
                            type="text"
                            value={loginData.full_name}
                            onChange={(e) => setLoginData({ ...loginData, full_name: e.target.value })}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Иван Иванов"
                        />
                    </div>
                </div>

                <button
                    onClick={handleLogin}
                    disabled={loading || !loginData.telegram_username}
                    className={`w-full mt-6 py-2 rounded-lg transition-colors ${loading || !loginData.telegram_username
                        ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                >
                    {loading ? 'Вход...' : 'Войти'}
                </button>
            </div>
        </div>
    );

    // Рендеринг модалки деталей задачи
    const renderTaskDetailsModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">{selectedTaskDetails?.title}</h3>
                    <button
                        onClick={() => {
                            setShowTaskDetails(false);
                            setSelectedTaskDetails(null);
                        }}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {selectedTaskDetails && (
                    <div className="space-y-3">
                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Описание:</h4>
                            <p className="text-gray-600">{selectedTaskDetails.description || 'Нет описания'}</p>
                        </div>

                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Срок выполнения:</h4>
                            <p className="text-gray-600">
                                {selectedTaskDetails.dueDate ?
                                    new Date(selectedTaskDetails.dueDate).toLocaleDateString() :
                                    'Не установлен'}
                                {isTaskUrgent(selectedTaskDetails) && (
                                    <span className="text-red-600 ml-2 font-medium">(Просрочено)</span>
                                )}
                            </p>
                        </div>

                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Исполнитель:</h4>
                            <p className="text-gray-600">
                                {selectedTaskDetails.assignee ?
                                    selectedTaskDetails.assignee.replace('@@', '@') :
                                    'Не назначен'}
                            </p>
                        </div>

                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Создатель:</h4>
                            <p className="text-gray-600">
                                {selectedTaskDetails.creator ?
                                    selectedTaskDetails.creator.replace('@@', '@') :
                                    'Неизвестно'}
                            </p>
                        </div>

                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Статус:</h4>
                            <select
                                value={selectedTaskDetails.status}
                                onChange={(e) => handleStatusChange(selectedTaskDetails.id, e.target.value)}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="todo">К выполнению</option>
                                <option value="in_progress">В процессе</option>
                                <option value="done">Выполнено</option>
                            </select>
                        </div>

                        <div>
                            <h4 className="font-medium text-gray-700 mb-1">Приоритет:</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${priorities.find(p => p.value === selectedTaskDetails.priority)?.color
                                }`}>
                                {priorities.find(p => p.value === selectedTaskDetails.priority)?.label}
                            </span>
                        </div>

                        {selectedTaskDetails.tags && selectedTaskDetails.tags.length > 0 && (
                            <div>
                                <h4 className="font-medium text-gray-700 mb-1">Теги:</h4>
                                <div className="flex flex-wrap gap-1">
                                    {selectedTaskDetails.tags.map((tag, idx) => (
                                        <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="pt-4 border-t">
                            <button
                                onClick={() => {
                                    setEditingTask(selectedTaskDetails);
                                    setShowTaskDetails(false);
                                    setShowTaskModal(true);
                                }}
                                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 mb-2"
                            >
                                Редактировать задачу
                            </button>
                            <button
                                onClick={() => deleteTask(selectedTaskDetails.id)}
                                className="w-full bg-red-600 text-white py-2 rounded-lg hover:bg-red-700"
                            >
                                Удалить задачу
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );

    // Рендеринг модалки профиля
    const renderProfileModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-96 overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">Мой профиль</h3>
                    <button
                        onClick={() => setShowProfile(false)}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {currentUser && (
                    <div className="space-y-6">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </div>
                            <div>
                                <h4 className="font-semibold text-lg">{currentUser.full_name}</h4>
                                <p className="text-gray-600">{currentUser.telegram_username}</p>
                                <p className="text-sm text-gray-500">Роль: {currentUser.role}</p>
                            </div>
                        </div>

                        <div className="border-t pt-4">
                            <h4 className="font-semibold mb-2">Мои задачи:</h4>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-50 p-3 rounded-lg">
                                    <div className="flex justify-between mb-1">
                                        <span>Всего назначенных:</span>
                                        <span className="font-medium">
                                            {tasks.filter(task => task.assignee === currentUser.telegram_username).length}
                                        </span>
                                    </div>
                                    <div className="flex justify-between mb-1">
                                        <span>Созданных мной:</span>
                                        <span className="font-medium">
                                            {tasks.filter(task => task.creator === currentUser.telegram_username).length}
                                        </span>
                                    </div>
                                    <div className="flex justify-between mb-1">
                                        <span>Выполнено:</span>
                                        <span className="font-medium text-green-600">
                                            {tasks.filter(task =>
                                                (task.assignee === currentUser.telegram_username ||
                                                    task.creator === currentUser.telegram_username) &&
                                                task.status === 'done'
                                            ).length}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Просрочено:</span>
                                        <span className="font-medium text-red-600">
                                            {tasks.filter(task =>
                                                (task.assignee === currentUser.telegram_username ||
                                                    task.creator === currentUser.telegram_username) &&
                                                task.dueDate && isTaskUrgent(task)
                                            ).length}
                                        </span>
                                    </div>
                                </div>

                                <div className="bg-gray-50 p-3 rounded-lg">
                                    <h5 className="font-semibold mb-2">Все пользователи системы:</h5>
                                    <div className="space-y-2 max-h-40 overflow-y-auto">
                                        {allRegisteredUsers.map(user => (
                                            <div key={user.telegram_username}
                                                className={`flex items-center justify-between text-sm p-1 rounded ${user.telegram_username === currentUser.telegram_username ? 'bg-blue-50' : ''}`}>
                                                <div className="flex items-center gap-2">
                                                    <div className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                                    <span>{user.full_name}</span>
                                                </div>
                                                <div className="flex flex-col text-right">
                                                    <span className="text-gray-500 text-xs">{user.telegram_username}</span>
                                                    <span className={`px-1 py-0.5 text-xs rounded ${user.role === 'admin' ? 'bg-red-100 text-red-800' :
                                                        user.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                                                            user.role === 'member' ? 'bg-green-100 text-green-800' :
                                                                'bg-gray-100 text-gray-800'
                                                        }`}>
                                                        {user.role}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2 text-center">
                                        Всего пользователей: {allRegisteredUsers.length}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={() => {
                                setShowProfile(false);
                                setActiveView('board');
                                toggleMyTasksFilter();
                            }}
                            className={`w-full py-2 rounded-lg transition-colors ${myTasksFilter
                                ? 'bg-gray-600 text-white hover:bg-gray-700'
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                                }`}
                        >
                            {myTasksFilter ? 'Показать все задачи' : 'Показать только мои задачи'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );

    // Рендеринг доски
    const renderBoardView = () => (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-4">
                    <h2 className="text-2xl font-bold text-gray-800">Канбан-доска</h2>
                    {myTasksFilter && (
                        <span className="bg-blue-100 text-blue-800 text-sm px-3 py-1 rounded-full">
                            Показаны только мои задачи
                        </span>
                    )}
                    {lastUpdateTime && (
                        <span className="text-sm text-gray-500">
                            Обновлено: {lastUpdateTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    )}
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={refreshData}
                        className="flex items-center gap-2 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
                        title="Обновить задачи"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Обновить
                    </button>
                    <button
                        onClick={toggleMyTasksFilter}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${myTasksFilter
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {myTasksFilter ? 'Все задачи' : 'Мои задачи'}
                    </button>
                    <button
                        onClick={() => setShowColumnModal(true)}
                        className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        Добавить колонку
                    </button>
                    <button
                        onClick={handleExportTasks}
                        className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Экспорт CSV
                    </button>
                    <button
                        onClick={() => setShowLLMAnalysis(true)}
                        className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        Анализ AI
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {columns.map((column) => (
                    <div
                        key={column.id}
                        className="bg-gray-50 rounded-lg p-4 min-h-96"
                        style={{ backgroundColor: `${column.color}10` }}
                    >
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-semibold text-lg" style={{ color: column.color }}>
                                {column.title}
                            </h3>
                            <span className="bg-gray-200 text-gray-700 text-xs px-2 py-1 rounded">
                                {filteredTasks.filter(task => task.columnId === column.id).length}
                            </span>
                        </div>

                        <div
                            className={`min-h-48 rounded-lg p-2 transition-colors ${dragOverColumn === column.id ? 'bg-blue-200 border-2 border-dashed border-blue-400' : ''
                                }`}
                            onDragOver={(e) => handleColumnDragOver(e, column.id)}
                            onDragLeave={handleColumnDragLeave}
                            onDrop={(e) => handleColumnDrop(e, column.id)}
                        >
                            {filteredTasks
                                .filter(task => task.columnId === column.id)
                                .map((task) => (
                                    <div
                                        key={task.id}
                                        draggable
                                        onDragStart={(e) => handleTaskDragStart(e, task)}
                                        className={`bg-white rounded-lg p-4 mb-3 shadow-sm border ${isTaskUrgent(task)
                                            ? 'border-red-400 bg-red-50'
                                            : 'border-gray-200'
                                            } cursor-move hover:shadow-md transition-all`}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-medium text-gray-800">{task.title}</h4>
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={() => {
                                                        setEditingTask(task);
                                                        setShowTaskModal(true);
                                                    }}
                                                    className="text-gray-400 hover:text-gray-600"
                                                    title="Редактировать"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                    </svg>
                                                </button>
                                                <button
                                                    onClick={() => showTaskDetailModal(task)}
                                                    className="text-gray-400 hover:text-gray-600"
                                                    title="Детали"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h1m0 0h-1m1 0v4m-5-6h.01M6 16h.01M9 10h.01" />
                                                    </svg>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="text-sm text-gray-600 mb-2 line-clamp-2">
                                            {task.description}
                                        </div>
                                        <div className="mb-2">
                                            <select
                                                value={task.status}
                                                onChange={(e) => handleStatusChange(task.id, e.target.value)}
                                                className="w-full p-1 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                                            >
                                                <option value="todo">К выполнению</option>
                                                <option value="in_progress">В процессе</option>
                                                <option value="done">Выполнено</option>
                                            </select>
                                        </div>
                                        {task.dueDate && (
                                            <div className={`flex items-center gap-1 text-xs mb-2 ${isTaskUrgent(task) ? 'text-red-600 font-medium' : 'text-gray-500'
                                                }`}>
                                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                                {new Date(task.dueDate).toLocaleDateString()}
                                                {isTaskUrgent(task) && (
                                                    <span className="text-red-500">*</span>
                                                )}
                                            </div>
                                        )}
                                        {task.assignee && (
                                            <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                                </svg>
                                                {task.assignee.replace('@@', '@')}
                                            </div>
                                        )}
                                        <div className="flex flex-wrap gap-1 mb-2">
                                            {task.tags.map((tag, idx) => (
                                                <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                        <div className={`inline-block px-2 py-1 rounded text-xs font-medium ${priorities.find(p => p.value === task.priority)?.color}`}>
                                            {priorities.find(p => p.value === task.priority)?.label}
                                        </div>
                                    </div>
                                ))}
                        </div>

                        <button
                            onClick={() => {
                                setSelectedColumnId(column.id);
                                setShowTaskModal(true);
                            }}
                            className="w-full text-left p-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
                        >
                            <svg className="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );

    // Рендеринг документации
    const renderDocsView = () => (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Документация</h2>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowFolderModal(true)}
                        className="flex items-center gap-2 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        Новая папка
                    </button>
                    <button
                        onClick={() => setShowDocModal(true)}
                        className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        Новый документ
                    </button>
                </div>
            </div>

            <div className="flex gap-6">
                <div className="w-1/4">
                    <div className="mb-4">
                        <div className="relative">
                            <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                placeholder="Поиск в документации..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <h3 className="font-semibold text-gray-700 mb-2">Структура документов</h3>
                        {Object.entries(documentTree).map(([folder, folderDocs]) => (
                            <div key={folder} className="border rounded-lg">
                                <div
                                    className="flex items-center justify-between p-2 bg-gray-50 hover:bg-gray-100 cursor-pointer rounded-t-lg"
                                    onClick={() => toggleFolder(folder)}
                                >
                                    <div className="flex items-center gap-2">
                                        <svg className={`w-4 h-4 text-blue-500 transition-transform ${expandedFolders.has(folder) ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                        <span className="text-sm font-medium">{folder} ({folderDocs.length})</span>
                                    </div>
                                </div>
                                {expandedFolders.has(folder) && (
                                    <div className="pl-6 py-1 space-y-1">
                                        {folderDocs.length > 0 ? (
                                            folderDocs.map((doc) => (
                                                <div
                                                    key={doc.id}
                                                    onClick={() => setSelectedDoc(doc)}
                                                    className={`flex items-center gap-2 p-1 rounded cursor-pointer text-sm ${selectedDoc?.id === doc.id ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100 text-gray-700'
                                                        }`}
                                                >
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                    <span className="truncate">{doc.name}</span>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="text-xs text-gray-500 italic p-1">
                                                Нет документов
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="w-3/4">
                    {selectedDoc ? (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                            <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                                <h3 className="font-semibold text-lg">{selectedDoc.name}</h3>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => {
                                            setEditingDoc(selectedDoc);
                                            setIsEditingDoc(true);
                                        }}
                                        className="p-2 text-gray-600 hover:text-gray-800"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            {isEditingDoc && editingDoc ? (
                                <div className="p-4">
                                    <textarea
                                        value={editingDoc.content}
                                        onChange={(e) => setEditingDoc({ ...editingDoc, content: e.target.value })}
                                        className="w-full h-96 p-3 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="Напишите контент в формате Markdown..."
                                    />
                                    <div className="flex gap-2 mt-4">
                                        <button
                                            onClick={updateDoc}
                                            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                            Сохранить
                                        </button>
                                        <button
                                            onClick={() => setIsEditingDoc(false)}
                                            className="flex items-center gap-2 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition-colors"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                            </svg>
                                            Отмена
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="p-4">
                                    <div
                                        className="prose max-w-none"
                                        dangerouslySetInnerHTML={{ __html: renderMarkdown(selectedDoc.content) }}
                                    />
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center text-gray-500">
                            Выберите документ для просмотра или редактирования
                        </div>
                    )}
                </div>
            </div>
        </div>
    );

    // Рендеринг календаря
    const renderCalendarView = () => {
        const monthYear = currentDate.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
        const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

        return (
            <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-800">Календарь задач</h2>
                    <div className="flex gap-4 items-center">
                        <div className="flex gap-2">
                            <button
                                onClick={() => setCalendarView('day')}
                                className={`px-3 py-1 rounded-lg text-sm ${calendarView === 'day' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
                                    }`}
                            >
                                День
                            </button>
                            <button
                                onClick={() => setCalendarView('week')}
                                className={`px-3 py-1 rounded-lg text-sm ${calendarView === 'week' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
                                    }`}
                            >
                                Неделя
                            </button>
                            <button
                                onClick={() => setCalendarView('month')}
                                className={`px-3 py-1 rounded-lg text-sm ${calendarView === 'month' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
                                    }`}
                            >
                                Месяц
                            </button>
                        </div>
                        <button
                            onClick={() => {
                                const newDate = new Date(currentDate);
                                newDate.setMonth(newDate.getMonth() - 1);
                                setCurrentDate(newDate);
                            }}
                            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                        >
                            &larr;
                        </button>
                        <span className="font-medium">
                            {monthYear}
                        </span>
                        <button
                            onClick={() => {
                                const newDate = new Date(currentDate);
                                newDate.setMonth(newDate.getMonth() + 1);
                                setCurrentDate(newDate);
                            }}
                            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                        >
                            &rarr;
                        </button>
                        <button
                            onClick={refreshData}
                            className="flex items-center gap-2 bg-gray-600 text-white px-3 py-1 rounded-lg hover:bg-gray-700 transition-colors text-sm"
                            title="Обновить задачи"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Обновить
                        </button>
                    </div>
                </div>

                {calendarView === 'month' && (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                        <div className="grid grid-cols-7 border-b border-gray-200">
                            {weekDays.map(day => (
                                <div key={day} className="text-center font-semibold text-gray-700 py-3">
                                    {day}
                                </div>
                            ))}
                        </div>
                        <div className="grid grid-cols-7 gap-px bg-gray-200">
                            {days.map((day, index) => {
                                const isToday = day && day.toDateString() === today.toDateString();
                                const dayTasks = day ? getTasksForDay(day) : [];
                                const hasUrgentTasks = dayTasks.some(task => isTaskUrgent(task));
                                const isCurrentMonth = day && day.getMonth() === currentDate.getMonth();

                                return (
                                    <div
                                        key={index}
                                        className={`min-h-32 p-2 ${isToday ? 'bg-blue-50' : 'bg-white'} ${!isCurrentMonth ? 'text-gray-400' : ''} ${hasUrgentTasks ? 'border-l-4 border-red-500' : ''}`}
                                        onClick={() => {
                                            if (day) {
                                                setCurrentDate(day);
                                                if (dayTasks.length > 0) {
                                                    setSelectedCalendarTask(dayTasks[0]);
                                                }
                                            }
                                        }}
                                    >
                                        {day && (
                                            <>
                                                <div className={`text-sm font-medium mb-1 ${isToday ? 'text-blue-600' : 'text-gray-700'
                                                    }`}>
                                                    {day.getDate()}
                                                </div>
                                                <div className="space-y-1 max-h-20 overflow-y-auto">
                                                    {dayTasks.map(task => (
                                                        <div
                                                            key={task.id}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                showTaskDetailModal(task);
                                                            }}
                                                            className={`text-xs px-2 py-1 rounded truncate cursor-pointer ${isTaskUrgent(task)
                                                                ? 'bg-red-100 text-red-800 border border-red-300 hover:bg-red-200'
                                                                : 'bg-blue-50 text-blue-800 hover:bg-blue-100'
                                                                }`}
                                                            title={`${task.title} (${task.assignee ? task.assignee.replace('@@', '@') : 'Не назначен'})`}
                                                        >
                                                            <div className="truncate">{task.title}</div>
                                                            <div className="text-xs text-gray-500 truncate">
                                                                {task.assignee ? task.assignee.replace('@@', '@') : 'Не назначен'}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                                {dayTasks.length > 3 && (
                                                    <div className="text-xs text-gray-500 mt-1">
                                                        +{dayTasks.length - 3} еще
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {calendarView === 'week' && (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                        <div className="grid grid-cols-8 border-b border-gray-200">
                            <div className="font-semibold text-gray-700 py-3"></div>
                            {Array.from({ length: 7 }).map((_, i) => {
                                const date = new Date(currentDate);
                                date.setDate(currentDate.getDate() - currentDate.getDay() + i + 1);
                                return (
                                    <div key={i} className="text-center font-semibold text-gray-700 py-3">
                                        {date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric' })}
                                    </div>
                                );
                            })}
                        </div>
                        <div className="divide-y divide-gray-200">
                            {tasks.filter(task => task.dueDate).map(task => (
                                <div key={task.id} className="grid grid-cols-8 hover:bg-gray-50">
                                    <div className="p-3">
                                        <div className="font-medium">{task.title}</div>
                                        <div className="text-sm text-gray-500">
                                            {task.assignee ? task.assignee.replace('@@', '@') : 'Не назначен'}
                                        </div>
                                    </div>
                                    {Array.from({ length: 7 }).map((_, i) => {
                                        const date = new Date(currentDate);
                                        date.setDate(currentDate.getDate() - currentDate.getDay() + i + 1);
                                        const taskDate = new Date(task.dueDate);
                                        const isSameDay = date.toDateString() === taskDate.toDateString();

                                        return (
                                            <div key={i} className="p-3 text-center">
                                                {isSameDay && (
                                                    <button
                                                        onClick={() => showTaskDetailModal(task)}
                                                        className={`px-2 py-1 rounded text-xs ${isTaskUrgent(task)
                                                            ? 'bg-red-100 text-red-800 border border-red-300'
                                                            : 'bg-blue-100 text-blue-800'
                                                            }`}
                                                    >
                                                        ✓
                                                    </button>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {calendarView === 'day' && (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                        <div className="p-4 border-b border-gray-200">
                            <h3 className="font-semibold">
                                {currentDate.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                            </h3>
                        </div>
                        <div className="p-4">
                            {getTasksForDay(currentDate).length > 0 ? (
                                <div className="space-y-3">
                                    {getTasksForDay(currentDate).map(task => (
                                        <div
                                            key={task.id}
                                            className={`p-4 border rounded-lg cursor-pointer hover:shadow-md ${isTaskUrgent(task)
                                                ? 'border-red-300 bg-red-50'
                                                : 'border-gray-200'
                                                }`}
                                            onClick={() => showTaskDetailModal(task)}
                                        >
                                            <div className="flex justify-between items-start">
                                                <h4 className="font-medium text-gray-800">{task.title}</h4>
                                                <span className={`px-2 py-1 rounded text-xs ${task.status === 'done' ? 'bg-green-100 text-green-800' :
                                                    task.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                                                        'bg-gray-100 text-gray-800'
                                                    }`}>
                                                    {task.status === 'done' ? 'Выполнено' :
                                                        task.status === 'in_progress' ? 'В процессе' : 'К выполнению'}
                                                </span>
                                            </div>
                                            <div className="text-sm text-gray-600 mt-1">{task.description}</div>
                                            <div className="flex justify-between items-center mt-2">
                                                <div className="text-sm text-gray-500">
                                                    {task.assignee ? task.assignee.replace('@@', '@') : 'Не назначен'}
                                                </div>
                                                <div className={`text-sm ${isTaskUrgent(task) ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
                                                    {task.priority}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-500">
                                    Нет задач на этот день
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // Рендеринг модалки задачи
    const renderTaskModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-96 overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">
                        {editingTask ? 'Редактировать задачу' : 'Создать новую задачу'}
                    </h3>
                    <button
                        onClick={() => {
                            setShowTaskModal(false);
                            if (!editingTask) {
                                resetTaskForm();
                                setSelectedColumnId(null);
                            }
                        }}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Название <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={editingTask ? editingTask.title : newTask.title}
                            onChange={(e) => {
                                if (editingTask) {
                                    setEditingTask({ ...editingTask, title: e.target.value });
                                } else {
                                    setNewTask({ ...newTask, title: e.target.value });
                                }
                                if (taskFormErrors.title) {
                                    setTaskFormErrors(prev => ({ ...prev, title: '' }));
                                }
                            }}
                            className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${taskFormErrors.title ? 'border-red-500' : 'border-gray-300'
                                }`}
                            placeholder="Название задачи"
                        />
                        {taskFormErrors.title && (
                            <p className="text-red-500 text-xs mt-1">{taskFormErrors.title}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                        <textarea
                            value={editingTask ? editingTask.description : newTask.description}
                            onChange={(e) => {
                                if (editingTask) {
                                    setEditingTask({ ...editingTask, description: e.target.value });
                                } else {
                                    setNewTask({ ...newTask, description: e.target.value });
                                }
                            }}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Описание задачи (поддерживает Markdown)"
                            rows="3"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Срок выполнения <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="date"
                            value={editingTask ? editingTask.dueDate : newTask.dueDate}
                            onChange={(e) => {
                                if (editingTask) {
                                    setEditingTask({ ...editingTask, dueDate: e.target.value });
                                } else {
                                    setNewTask({ ...newTask, dueDate: e.target.value });
                                }
                                if (taskFormErrors.dueDate) {
                                    setTaskFormErrors(prev => ({ ...prev, dueDate: '' }));
                                }
                            }}
                            className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${taskFormErrors.dueDate ? 'border-red-500' : 'border-gray-300'
                                }`}
                        />
                        {taskFormErrors.dueDate && (
                            <p className="text-red-500 text-xs mt-1">{taskFormErrors.dueDate}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Исполнитель <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={editingTask ? editingTask.assignee : newTask.assignee}
                            onChange={(e) => {
                                if (editingTask) {
                                    setEditingTask({ ...editingTask, assignee: e.target.value });
                                } else {
                                    setNewTask({ ...newTask, assignee: e.target.value });
                                }
                                if (taskFormErrors.assignee) {
                                    setTaskFormErrors(prev => ({ ...prev, assignee: '' }));
                                }
                            }}
                            className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${taskFormErrors.assignee ? 'border-red-500' : 'border-gray-300'
                                }`}
                        >
                            <option value="">Выберите исполнителя</option>
                            {users.map(user => (
                                <option key={user.telegram_username} value={user.telegram_username}>
                                    {user.telegram_username} - {user.full_name}
                                </option>
                            ))}
                        </select>
                        {taskFormErrors.assignee && (
                            <p className="text-red-500 text-xs mt-1">{taskFormErrors.assignee}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Приоритет</label>
                        <select
                            value={editingTask ? editingTask.priority : newTask.priority}
                            onChange={(e) => {
                                if (editingTask) {
                                    setEditingTask({ ...editingTask, priority: e.target.value });
                                } else {
                                    setNewTask({ ...newTask, priority: e.target.value });
                                }
                            }}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            {priorities.map(priority => (
                                <option key={priority.value} value={priority.value}>
                                    {priority.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Теги</label>
                        <div className="flex gap-2 mb-2">
                            <input
                                type="text"
                                value={newTag}
                                onChange={(e) => setNewTag(e.target.value)}
                                className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="Добавить тег"
                                onKeyPress={(e) => {
                                    if (e.key === 'Enter' && newTag.trim()) {
                                        const tags = editingTask ? editingTask.tags : newTask.tags;
                                        if (editingTask) {
                                            setEditingTask({ ...editingTask, tags: [...tags, newTag.trim()] });
                                        } else {
                                            setNewTask({ ...newTask, tags: [...tags, newTag.trim()] });
                                        }
                                        setNewTag('');
                                    }
                                }}
                            />
                            <button
                                onClick={() => {
                                    if (newTag.trim()) {
                                        const tags = editingTask ? editingTask.tags : newTask.tags;
                                        if (editingTask) {
                                            setEditingTask({ ...editingTask, tags: [...tags, newTag.trim()] });
                                        } else {
                                            setNewTask({ ...newTask, tags: [...tags, newTag.trim()] });
                                        }
                                        setNewTag('');
                                    }
                                }}
                                className="bg-blue-600 text-white px-3 rounded-lg hover:bg-blue-700"
                            >
                                Добавить
                            </button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {(editingTask ? editingTask.tags : newTask.tags).map((tag, index) => (
                                <span
                                    key={index}
                                    className="bg-blue-100 text-blue-800 px-2 py-1 rounded flex items-center gap-1"
                                >
                                    {tag}
                                    <button
                                        onClick={() => {
                                            const tags = editingTask ? editingTask.tags : newTask.tags;
                                            const newTags = tags.filter((_, i) => i !== index);
                                            if (editingTask) {
                                                setEditingTask({ ...editingTask, tags: newTags });
                                            } else {
                                                setNewTask({ ...newTask, tags: newTags });
                                            }
                                        }}
                                        className="text-blue-600 hover:text-blue-800"
                                    >
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </span>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <button
                        onClick={editingTask ? updateTask : createTask}
                        className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        {editingTask ? 'Обновить задачу' : 'Создать задачу'}
                    </button>
                    {editingTask && (
                        <button
                            onClick={() => deleteTask(editingTask.id)}
                            className="bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition-colors"
                        >
                            Удалить
                        </button>
                    )}
                </div>
            </div>
        </div>
    );

    // Рендеринг модалки LLM анализа
    const renderLLMAnalysisModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-96 overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">AI Анализ продуктивности</h3>
                    <button
                        onClick={() => setShowLLMAnalysis(false)}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {analysisResult ? (
                    <div className="space-y-4">
                        <div className="bg-blue-50 p-4 rounded-lg">
                            <h4 className="font-semibold text-blue-800 mb-2">Отчет #{analysisResult.report_id}</h4>
                            <p className="text-sm text-blue-600">
                                Сгенерирован: {new Date(analysisResult.generated_at).toLocaleString()}
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Статистика</h5>
                                <ul className="space-y-1 text-sm">
                                    <li>Всего задач: {analysisResult.analysis?.summary?.total_tasks || 0}</li>
                                    <li>Выполнено: {analysisResult.analysis?.summary?.completed || 0}</li>
                                    <li>Процент выполнения: {analysisResult.analysis?.summary?.completion_rate || '0%'}</li>
                                    <li>В процессе: {analysisResult.analysis?.summary?.in_progress || 0}</li>
                                    <li>Просрочено: {analysisResult.analysis?.summary?.overdue || 0}</li>
                                </ul>
                            </div>

                            <div className="bg-green-50 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Продуктивность</h5>
                                <p className="text-sm">Оценка команды: {analysisResult.analysis?.productivity_metrics?.team_productivity_score || 0}/10</p>
                            </div>
                        </div>

                        {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                            <div className="bg-yellow-50 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Рекомендации</h5>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    {analysisResult.recommendations.map((rec, idx) => (
                                        <li key={idx}>{rec}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {analysisResult.predictions && (
                            <div className="bg-purple-50 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Прогнозы</h5>
                                <p className="text-sm">На следующую неделю: {analysisResult.predictions.next_week_completion}</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <button
                            onClick={handleLLMAnalysis}
                            disabled={loading}
                            className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                        >
                            {loading ? 'Анализ выполняется...' : 'Запустить анализ'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );

    // Рендеринг основной разметки
    return (
        <div className="min-h-screen bg-gray-50">
            {/* Навигация */}
            <nav className="bg-white shadow-sm border-b border-gray-200">
                <div className="flex items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                            <svg className="text-white w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h1 className="text-xl font-bold text-gray-800">Менеджер проектов</h1>
                    </div>

                    <div className="flex gap-1">
                        <button
                            onClick={() => setActiveView('board')}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${activeView === 'board'
                                ? 'bg-blue-100 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            Доска
                        </button>
                        <button
                            onClick={() => setActiveView('docs')}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${activeView === 'docs'
                                ? 'bg-blue-100 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Документы
                        </button>
                        <button
                            onClick={() => setActiveView('calendar')}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${activeView === 'calendar'
                                ? 'bg-blue-100 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            Календарь
                        </button>
                    </div>

                    {isAuthenticated ? (
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setShowProfile(true)}
                                className="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-lg hover:bg-gray-200 transition-colors"
                            >
                                <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                                <span className="text-sm text-gray-700">
                                    {currentUser?.telegram_username || 'user'}
                                </span>
                                {myTasksFilter && (
                                    <span className="bg-blue-100 text-blue-800 text-xs px-1.5 py-0.5 rounded-full">
                                        {myTasks.length}
                                    </span>
                                )}
                            </button>
                            <button
                                onClick={handleLogout}
                                className="text-gray-600 hover:text-gray-800 text-sm"
                            >
                                Выйти
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={() => setShowLoginModal(true)}
                            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                        >
                            Войти
                        </button>
                    )}
                </div>
            </nav>

            {/* Основной контент */}
            <main>
                {!isAuthenticated ? (
                    <div className="flex flex-col items-center justify-center min-h-[80vh]">
                        <h2 className="text-2xl font-bold text-gray-800 mb-4">Добро пожаловать!</h2>
                        <p className="text-gray-600 mb-6">Для начала работы войдите в систему</p>
                        <button
                            onClick={() => setShowLoginModal(true)}
                            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
                        >
                            Войти через Telegram
                        </button>
                    </div>
                ) : (
                    <>
                        {activeView === 'board' && renderBoardView()}
                        {activeView === 'docs' && renderDocsView()}
                        {activeView === 'calendar' && renderCalendarView()}
                    </>
                )}
            </main>

            {/* Модальные окна */}
            {showLoginModal && renderLoginModal()}
            {showTaskModal && renderTaskModal()}
            {showLLMAnalysis && renderLLMAnalysisModal()}
            {showTaskDetails && renderTaskDetailsModal()}
            {showProfile && renderProfileModal()}
            {showDocModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">Создать новый документ</h3>
                            <button
                                onClick={() => setShowDocModal(false)}
                                className="text-gray-500 hover:text-gray-700"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Имя документа <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={newDoc.name}
                                    onChange={(e) => {
                                        setNewDoc({ ...newDoc, name: e.target.value });
                                        if (docFormErrors.name) {
                                            setDocFormErrors(prev => ({ ...prev, name: '' }));
                                        }
                                    }}
                                    className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${docFormErrors.name ? 'border-red-500' : 'border-gray-300'
                                        }`}
                                    placeholder="Имя документа"
                                />
                                {docFormErrors.name && (
                                    <p className="text-red-500 text-xs mt-1">{docFormErrors.name}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Папка</label>
                                <select
                                    value={newDoc.folder}
                                    onChange={(e) => setNewDoc({ ...newDoc, folder: e.target.value })}
                                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="">Выберите папку</option>
                                    {docFolders.map(folder => (
                                        <option key={folder} value={folder}>{folder}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Содержимое</label>
                                <textarea
                                    value={newDoc.content}
                                    onChange={(e) => setNewDoc({ ...newDoc, content: e.target.value })}
                                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Содержимое документа (Markdown)"
                                    rows="5"
                                />
                            </div>
                        </div>

                        <button
                            onClick={createDoc}
                            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors mt-6"
                        >
                            Создать документ
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default App;