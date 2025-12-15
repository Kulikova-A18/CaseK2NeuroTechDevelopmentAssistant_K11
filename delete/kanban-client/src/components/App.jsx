import React, { useState, useRef, useEffect } from 'react';

// Данные пользователей (симуляция интеграции с Telegram)
const mockUsers = [
    { id: 1, username: 'john_doe', name: 'John Doe' },
    { id: 2, username: 'jane_smith', name: 'Jane Smith' },
    { id: 3, username: 'alex_wilson', name: 'Alex Wilson' },
    { id: 4, username: 'sarah_johnson', name: 'Sarah Johnson' }
];

// Начальные данные доски
const initialColumns = [
    { id: 'col-1', title: 'К выполнению', color: '#00008B' },
    { id: 'col-2', title: 'В процессе', color: '#00008B' },
    { id: 'col-3', title: 'Выполнено', color: '#00008B' }
];

const initialTasks = [];

const initialDocs = [
    { id: 'doc-1', name: 'Начало работы.md', content: '# Добро пожаловать в проект\n\nЭто ваше руководство по началу работы.', folder: 'Руководства', lastModified: new Date() },
    { id: 'doc-2', name: 'Документация API.md', content: '# Справочник по API\n\n## Конечные точки\n\n- `/api/tasks` - Получить все задачи', folder: 'Техническая', lastModified: new Date() }
];

const priorities = [
    { value: 'low', label: 'Низкий', color: 'bg-green-100 text-green-800' },
    { value: 'medium', label: 'Средний', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'high', label: 'Высокий', color: 'bg-orange-100 text-orange-800' },
    { value: 'critical', label: 'Критический', color: 'bg-red-100 text-red-800' }
];

const App = () => {
    // Состояние доски
    const [columns, setColumns] = useState(initialColumns);
    const [tasks, setTasks] = useState(initialTasks);
    const [activeView, setActiveView] = useState('board'); // 'board', 'docs', 'calendar'

    // Состояние документации
    const [docs, setDocs] = useState(initialDocs);
    const [selectedDoc, setSelectedDoc] = useState(null);
    const [docFolders, setDocFolders] = useState(['Руководства', 'Техническая', 'User Stories']);
    const [searchTerm, setSearchTerm] = useState('');
    const [isEditingDoc, setIsEditingDoc] = useState(false);
    const [expandedFolders, setExpandedFolders] = useState(new Set(['Руководства', 'Техническая', 'User Stories']));

    // Состояние календаря
    const [currentDate, setCurrentDate] = useState(new Date());
    const [calendarView, setCalendarView] = useState('month'); // 'month', 'week', 'day'
    const [selectedCalendarTask, setSelectedCalendarTask] = useState(null);

    // Состояние модальных окон
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [showColumnModal, setShowColumnModal] = useState(false);
    const [showDocModal, setShowDocModal] = useState(false);
    const [showFolderModal, setShowFolderModal] = useState(false);
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
        files: []
    });

    const [newColumn, setNewColumn] = useState({
        title: '',
        color: '#00008B'
    });

    const [newDoc, setNewDoc] = useState({
        name: '',
        content: '',
        folder: 'Руководства'
    });

    const [newFolder, setNewFolder] = useState('');

    const [newTag, setNewTag] = useState('');
    const [taskFormErrors, setTaskFormErrors] = useState({});
    const [docFormErrors, setDocFormErrors] = useState({});

    // Состояние drag and drop
    const [draggedTask, setDraggedTask] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);

    // Построение дерева документов
    const buildDocumentTree = () => {
        const tree = {};

        // Добавляем существующие папки
        docFolders.forEach(folder => {
            tree[folder] = [];
        });

        // Добавляем документы в соответствующие папки
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

    // Проверка, является ли задача срочной (просрочена или срок сегодня)
    const isTaskUrgent = (task) => {
        if (!task.dueDate) return false;
        const dueDate = new Date(task.dueDate);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        dueDate.setHours(0, 0, 0, 0);
        return dueDate <= today;
    };

    // Обработка начала перетаскивания задачи
    const handleTaskDragStart = (task) => {
        setDraggedTask(task);
    };

    // Обработка наведения на колонку
    const handleColumnDragOver = (e, columnId) => {
        e.preventDefault();
        setDragOverColumn(columnId);
    };

    // Обработка ухода курсора с колонки
    const handleColumnDragLeave = () => {
        setDragOverColumn(null);
    };

    // Обработка сброса задачи в колонку
    const handleColumnDrop = (columnId) => {
        if (!draggedTask) return;

        const updatedTasks = tasks.map(task => {
            if (task.id === draggedTask.id) {
                return { ...task, columnId };
            }
            return task;
        });

        setTasks(updatedTasks);
        setDraggedTask(null);
        setDragOverColumn(null);
    };

    // Валидация формы задачи
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

    // Валидация формы документа
    const validateDocForm = (docData) => {
        const errors = {};
        if (!docData.name?.trim()) {
            errors.name = 'Имя документа обязательно';
        }
        return errors;
    };

    // Создание задачи
    const createTask = () => {
        if (!selectedColumnId) return;

        const taskData = { ...newTask, columnId: selectedColumnId };
        const errors = validateTaskForm(taskData);

        if (Object.keys(errors).length > 0) {
            setTaskFormErrors(errors);
            return;
        }

        const task = {
            id: `task-${Date.now()}`,
            ...taskData,
            createdAt: new Date(),
            updatedAt: new Date()
        };
        setTasks(prevTasks => [...prevTasks, task]);
        resetTaskForm();
        setShowTaskModal(false);
        setSelectedColumnId(null);
    };

    // Обновление задачи
    const updateTask = () => {
        const errors = validateTaskForm(editingTask);

        if (Object.keys(errors).length > 0) {
            setTaskFormErrors(errors);
            return;
        }

        const updatedTasks = tasks.map(task =>
            task.id === editingTask.id
                ? { ...editingTask, updatedAt: new Date() }
                : task
        );
        setTasks(updatedTasks);
        setEditingTask(null);
        setShowTaskModal(false);
        setTaskFormErrors({});
    };

    // Удаление задачи
    const deleteTask = (taskId) => {
        setTasks(tasks.filter(task => task.id !== taskId));
        if (selectedCalendarTask?.id === taskId) {
            setSelectedCalendarTask(null);
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
            files: []
        });
        setNewTag('');
        setTaskFormErrors({});
    };

    // Создание колонки
    const createColumn = () => {
        const column = {
            id: `col-${Date.now()}`,
            ...newColumn
        };
        setColumns(prevColumns => [...prevColumns, column]);
        setNewColumn({ title: '', color: '#00008B' });
        setShowColumnModal(false);
    };

    // Обновление колонки
    const updateColumn = () => {
        const updatedColumns = columns.map(col =>
            col.id === editingColumn.id ? editingColumn : col
        );
        setColumns(updatedColumns);
        setEditingColumn(null);
        setShowColumnModal(false);
    };

    // Удаление колонки
    const deleteColumn = (columnId) => {
        setColumns(columns.filter(col => col.id !== columnId));
        setTasks(tasks.filter(task => task.columnId !== columnId));
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

        // Если папка новая, добавляем её в список папок
        if (!docFolders.includes(newDoc.folder)) {
            setDocFolders(prev => [...prev, newDoc.folder]);
            // Автоматически раскрываем новую папку
            setExpandedFolders(prev => new Set([...prev, newDoc.folder]));
        }

        setNewDoc({ name: '', content: '', folder: docFolders[0] || 'Руководства' });
        setDocFormErrors({});
        setShowDocModal(false);
    };

    // Создание папки
    const createFolder = () => {
        if (!newFolder.trim()) return;
        if (docFolders.includes(newFolder.trim())) return;

        setDocFolders(prev => [...prev, newFolder.trim()]);
        setNewFolder('');
        setShowFolderModal(false);
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

    // Удаление документа
    const deleteDoc = (docId) => {
        setDocs(docs.filter(doc => doc.id !== docId));
        if (selectedDoc?.id === docId) {
            setSelectedDoc(null);
        }
    };

    // Получение дней месяца для календаря
    const getDaysInMonth = (date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const days = [];

        // Добавляем пустые дни перед первым днем месяца
        for (let i = 0; i < firstDay.getDay(); i++) {
            days.push(null);
        }

        // Добавляем дни месяца
        for (let day = 1; day <= lastDay.getDate(); day++) {
            days.push(new Date(year, month, day));
        }

        return days;
    };

    // Получение задач для конкретной даты
    const getTasksForDate = (date) => {
        return tasks.filter(task => {
            if (!task.dueDate) return false;
            const dueDate = new Date(task.dueDate);
            return dueDate.toDateString() === date.toDateString();
        });
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

    const renderBoardView = () => (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Канбан-доска</h2>
                <button
                    onClick={() => setShowColumnModal(true)}
                    className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Добавить колонку
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
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
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                        setEditingColumn(column);
                                        setShowColumnModal(true);
                                    }}
                                    className="p-1 hover:bg-gray-200 rounded"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                </button>
                                <button
                                    onClick={() => deleteColumn(column.id)}
                                    className="p-1 hover:bg-red-100 rounded text-red-600"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        <div
                            className={`min-h-48 rounded-lg p-2 transition-colors ${dragOverColumn === column.id ? 'bg-blue-200 border-2 border-dashed border-blue-400' : ''
                                }`}
                            onDragOver={(e) => handleColumnDragOver(e, column.id)}
                            onDragLeave={handleColumnDragLeave}
                            onDrop={() => handleColumnDrop(column.id)}
                        >
                            {tasks
                                .filter(task => task.columnId === column.id)
                                .map((task) => (
                                    <div
                                        key={task.id}
                                        draggable
                                        onDragStart={() => handleTaskDragStart(task)}
                                        className={`bg-white rounded-lg p-4 mb-3 shadow-sm border ${isTaskUrgent(task)
                                            ? 'border-red-400 bg-red-50'
                                            : 'border-gray-200'
                                            } cursor-move hover:shadow-md transition-all`}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-medium text-gray-800">{task.title}</h4>
                                            <button
                                                onClick={() => {
                                                    setEditingTask(task);
                                                    setShowTaskModal(true);
                                                }}
                                                className="text-gray-400 hover:text-gray-600"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                </svg>
                                            </button>
                                        </div>
                                        <div className="text-sm text-gray-600 mb-2 line-clamp-2">
                                            {task.description}
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
                                                @{task.assignee}
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
                                    <button
                                        onClick={() => deleteDoc(selectedDoc.id)}
                                        className="p-2 text-red-600 hover:text-red-800"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
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

    const renderCalendarView = () => (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Календарь</h2>
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
                        onClick={() => setCurrentDate(new Date(today.getFullYear(), today.getMonth() - 1, 1))}
                        className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                    >
                        &larr;
                    </button>
                    <span className="font-medium">
                        {currentDate.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })}
                    </span>
                    <button
                        onClick={() => setCurrentDate(new Date(today.getFullYear(), today.getMonth() + 1, 1))}
                        className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                    >
                        &rarr;
                    </button>
                </div>
            </div>

            {calendarView === 'month' && (
                <div className="grid grid-cols-7 gap-1 bg-gray-100 p-2 rounded-lg">
                    {['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'].map(day => (
                        <div key={day} className="text-center font-semibold text-gray-700 py-2">
                            {day}
                        </div>
                    ))}
                    {days.map((day, index) => {
                        const isToday = day && day.toDateString() === today.toDateString();
                        const dayTasks = day ? getTasksForDate(day) : [];
                        const hasUrgentTasks = dayTasks.some(task => isTaskUrgent(task));

                        return (
                            <div
                                key={index}
                                className={`min-h-24 p-2 border border-gray-200 bg-white rounded ${isToday ? 'bg-blue-50 border-blue-300' : ''
                                    } ${hasUrgentTasks ? 'border-red-400 bg-red-50' : ''}`}
                            >
                                {day && (
                                    <>
                                        <div className={`text-sm font-medium mb-1 ${isToday ? 'text-blue-600' : 'text-gray-700'
                                            }`}>
                                            {day.getDate()}
                                        </div>
                                        <div className="space-y-1">
                                            {dayTasks.map(task => (
                                                <div
                                                    key={task.id}
                                                    onClick={() => setSelectedCalendarTask(task)}
                                                    className={`text-xs px-2 py-1 rounded truncate cursor-pointer ${isTaskUrgent(task)
                                                        ? 'bg-red-200 text-red-800 border border-red-300'
                                                        : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                                                        }`}
                                                >
                                                    {task.title}
                                                </div>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );

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
                                // Очистка ошибки при вводе
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
                                // Очистка ошибки при выборе даты
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
                                // Очистка ошибки при выборе исполнителя
                                if (taskFormErrors.assignee) {
                                    setTaskFormErrors(prev => ({ ...prev, assignee: '' }));
                                }
                            }}
                            className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${taskFormErrors.assignee ? 'border-red-500' : 'border-gray-300'
                                }`}
                        >
                            <option value="">Выберите исполнителя</option>
                            {mockUsers.map(user => (
                                <option key={user.id} value={user.username}>
                                    @{user.username} - {user.name}
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

    const renderColumnModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">
                        {editingColumn ? 'Редактировать колонку' : 'Создать новую колонку'}
                    </h3>
                    <button
                        onClick={() => {
                            setShowColumnModal(false);
                            if (!editingColumn) setNewColumn({ title: '', color: '#00008B' });
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
                        <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
                        <input
                            type="text"
                            value={editingColumn ? editingColumn.title : newColumn.title}
                            onChange={(e) => {
                                if (editingColumn) {
                                    setEditingColumn({ ...editingColumn, title: e.target.value });
                                } else {
                                    setNewColumn({ ...newColumn, title: e.target.value });
                                }
                            }}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Название колонки"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Цвет</label>
                        <div className="flex gap-2">
                            {['#00008B', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'].map(color => (
                                <button
                                    key={color}
                                    onClick={() => {
                                        if (editingColumn) {
                                            setEditingColumn({ ...editingColumn, color });
                                        } else {
                                            setNewColumn({ ...newColumn, color });
                                        }
                                    }}
                                    className={`w-8 h-8 rounded-full border-2 ${(editingColumn ? editingColumn.color : newColumn.color) === color
                                        ? 'border-gray-800'
                                        : 'border-transparent'
                                        }`}
                                    style={{ backgroundColor: color }}
                                />
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <button
                        onClick={editingColumn ? updateColumn : createColumn}
                        className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        {editingColumn ? 'Обновить колонку' : 'Создать колонку'}
                    </button>
                    {editingColumn && (
                        <button
                            onClick={() => deleteColumn(editingColumn.id)}
                            className="bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition-colors"
                        >
                            Удалить
                        </button>
                    )}
                </div>
            </div>
        </div>
    );

    const renderDocModal = () => (
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
                                // Очистка ошибки при вводе
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
                            {docFolders.map(folder => (
                                <option key={folder} value={folder}>
                                    {folder}
                                </option>
                            ))}
                        </select>
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
    );

    const renderFolderModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">Создать новую папку</h3>
                    <button
                        onClick={() => setShowFolderModal(false)}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Имя папки</label>
                        <input
                            type="text"
                            value={newFolder}
                            onChange={(e) => setNewFolder(e.target.value)}
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Имя новой папки"
                        />
                        {docFolders.includes(newFolder.trim()) && newFolder.trim() && (
                            <p className="text-red-500 text-xs mt-1">Папка с таким именем уже существует</p>
                        )}
                    </div>
                </div>

                <button
                    onClick={createFolder}
                    disabled={!newFolder.trim() || docFolders.includes(newFolder.trim())}
                    className={`w-full py-2 rounded-lg transition-colors mt-6 ${!newFolder.trim() || docFolders.includes(newFolder.trim())
                        ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                        : 'bg-gray-600 text-white hover:bg-gray-700'
                        }`}
                >
                    Создать папку
                </button>
            </div>
        </div>
    );

    const renderCalendarTaskModal = () => {
        if (!selectedCalendarTask) return null;

        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-96 overflow-y-auto">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-semibold">Подробности задачи</h3>
                        <button
                            onClick={() => setSelectedCalendarTask(null)}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <h4 className="font-medium text-gray-800">{selectedCalendarTask.title}</h4>
                        </div>

                        {selectedCalendarTask.description && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                                <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                                    {selectedCalendarTask.description}
                                </div>
                            </div>
                        )}

                        {selectedCalendarTask.dueDate && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Срок выполнения</label>
                                <div className="text-sm text-gray-600">
                                    {new Date(selectedCalendarTask.dueDate).toLocaleDateString('ru-RU')}
                                </div>
                            </div>
                        )}

                        {selectedCalendarTask.assignee && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Исполнитель</label>
                                <div className="text-sm text-gray-600">
                                    @{selectedCalendarTask.assignee}
                                </div>
                            </div>
                        )}

                        {selectedCalendarTask.tags && selectedCalendarTask.tags.length > 0 && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Теги</label>
                                <div className="flex flex-wrap gap-1">
                                    {selectedCalendarTask.tags.map((tag, idx) => (
                                        <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Приоритет</label>
                            <div className={`inline-block px-2 py-1 rounded text-xs font-medium ${priorities.find(p => p.value === selectedCalendarTask.priority)?.color}`}>
                                {priorities.find(p => p.value === selectedCalendarTask.priority)?.label}
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => {
                                    setEditingTask(selectedCalendarTask);
                                    setSelectedCalendarTask(null);
                                    setShowTaskModal(true);
                                }}
                                className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Редактировать
                            </button>
                            <button
                                onClick={() => {
                                    deleteTask(selectedCalendarTask.id);
                                    setSelectedCalendarTask(null);
                                }}
                                className="bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition-colors"
                            >
                                Удалить
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const today = new Date();
    const days = getDaysInMonth(currentDate);

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

                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-lg">
                            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                            <span className="text-sm text-gray-700">@john_doe</span>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Основной контент */}
            <main>
                {activeView === 'board' && renderBoardView()}
                {activeView === 'docs' && renderDocsView()}
                {activeView === 'calendar' && renderCalendarView()}
            </main>

            {/* Модальные окна */}
            {showTaskModal && renderTaskModal()}
            {showColumnModal && renderColumnModal()}
            {showDocModal && renderDocModal()}
            {showFolderModal && renderFolderModal()}
            {selectedCalendarTask && renderCalendarTaskModal()}
        </div>
    );
};

export default App;
