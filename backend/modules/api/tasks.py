"""
Tasks API endpoints.
Handles task CRUD operations and filtering.
"""

import json
import logging
from datetime import datetime, timedelta

from flask import request

from modules.models import TaskCreate, TaskUpdate
from modules.decorators import validate_request, generate_response, require_permission
from modules.constants import SystemConstants


class TasksAPI:
    """
    Tasks API endpoints.
    
    @param tasks_manager: CSV data manager for tasks
    @param users_manager: CSV data manager for users
    @param cache_manager: Cache manager instance
    @param auth_manager: Authentication manager instance
    @param config_manager: Configuration manager instance
    @param socketio: SocketIO instance for real-time updates
    """
    
    def __init__(self, tasks_manager, users_manager, cache_manager, auth_manager, config_manager, socketio):
        self.tasks_manager = tasks_manager
        self.users_manager = users_manager
        self.cache_manager = cache_manager
        self.auth_manager = auth_manager
        self.config_manager = config_manager
        self.socketio = socketio
    
    def get_tasks_endpoint(self):
        """
        Endpoint for getting task list with filtering and pagination.
        
        Query parameters:
            status: Filter by status (comma-separated)
            assignee: Filter by assignee
            creator: Filter by creator
            priority: Filter by priority (comma-separated)
            date_from: Tasks from date (YYYY-MM-DD)
            date_to: Tasks to date (YYYY-MM-DD)
            tags: Filter by tags (comma-separated)
            limit: Limit count (default 100)
            offset: Offset (default 0)
        
        @return: JSON with task list and pagination info
        """
        user_info = request.user_info
        logging.info(f"Task list request from user: {user_info['telegram_username']}")
        logging.debug(f"Query parameters: {dict(request.args)}")
        
        # Get filtering parameters
        status_filter = request.args.get('status', '').split(',')
        assignee_filter = request.args.get('assignee')
        creator_filter = request.args.get('creator')
        priority_filter = request.args.get('priority', '').split(',')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        tags_filter = request.args.get('tags', '').split(',')
        limit = min(int(request.args.get('limit', 100)), 500)  # Max 500
        offset = int(request.args.get('offset', 0))
        
        # Generate cache key
        cache_key = self.cache_manager.generate_key(
            'tasks_filter',
            user=user_info['telegram_username'],
            status=','.join(sorted(status_filter)) if status_filter[0] else '',
            assignee=assignee_filter or '',
            creator=creator_filter or '',
            priority=','.join(sorted(priority_filter)) if priority_filter[0] else '',
            date_from=date_from or '',
            date_to=date_to or '',
            tags=','.join(sorted(tags_filter)) if tags_filter[0] else '',
            limit=limit,
            offset=offset
        )
        
        # Check cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logging.debug(f"Using cached result for key: {cache_key}")
            return generate_response(cached_result, config_manager=self.config_manager)
        
        # Get all tasks
        all_tasks = self.tasks_manager.read_all()
        
        # Apply filters
        filtered_tasks = []
        for task in all_tasks:
            # Filter by status
            if status_filter and status_filter[0] and task.get('status') not in status_filter:
                continue
            
            # Filter by assignee
            if assignee_filter and task.get('assignee') != assignee_filter:
                continue
            
            # Filter by creator
            if creator_filter and task.get('creator') != creator_filter:
                continue
            
            # Filter by priority
            if priority_filter and priority_filter[0] and task.get('priority') not in priority_filter:
                continue
            
            # Filter by date
            try:
                created_at_str = task.get('created_at', '')
                if created_at_str:
                    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                    if date_from:
                        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                        if created_at.date() < date_from_dt.date():
                            continue
                    if date_to:
                        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                        if created_at.date() > date_to_dt.date():
                            continue
            except:
                pass
            
            # Filter by tags
            if tags_filter and tags_filter[0]:
                try:
                    task_tags = json.loads(task.get('tags', '[]'))
                    if not any(tag in task_tags for tag in tags_filter):
                        continue
                except:
                    continue
            
            filtered_tasks.append(task)
        
        # Pagination
        total = len(filtered_tasks)
        paginated_tasks = filtered_tasks[offset:offset + limit]
        
        # Enrich data with user names
        enriched_tasks = []
        for task in paginated_tasks:
            enriched_task = task.copy()
            
            # Add assignee name
            if task.get('assignee'):
                assignee_user = self.users_manager.find_one(telegram_username=task['assignee'])
                if assignee_user:
                    enriched_task['assignee_name'] = assignee_user.get('full_name')
            
            # Add creator name
            if task.get('creator'):
                creator_user = self.users_manager.find_one(telegram_username=task['creator'])
                if creator_user:
                    enriched_task['creator_name'] = creator_user.get('full_name')
            
            # Calculate days until deadline
            if task.get('due_date'):
                try:
                    due_date = datetime.strptime(task['due_date'], '%Y-%m-%d')
                    days_remaining = (due_date.date() - datetime.now().date()).days
                    enriched_task['days_remaining'] = days_remaining
                    enriched_task['is_overdue'] = days_remaining < 0
                except:
                    pass
            
            # Parse JSON tags
            if task.get('tags'):
                try:
                    enriched_task['tags'] = json.loads(task['tags'])
                except:
                    enriched_task['tags'] = []
            
            enriched_tasks.append(enriched_task)
        
        # Form response
        response_data = {
            'tasks': enriched_tasks,
            'pagination': {
                'total': total,
                'page': (offset // limit) + 1,
                'per_page': limit,
                'total_pages': (total + limit - 1) // limit
            },
            'filters_applied': {
                'status': status_filter if status_filter[0] else None,
                'assignee': assignee_filter,
                'creator': creator_filter,
                'priority': priority_filter if priority_filter[0] else None,
                'date_from': date_from,
                'date_to': date_to,
                'tags': tags_filter if tags_filter[0] else None
            }
        }
        
        # Save to cache
        self.cache_manager.set(cache_key, response_data)
        
        logging.info(f"Retrieved {len(enriched_tasks)} tasks by user {user_info['telegram_username']}")
        return generate_response(response_data, config_manager=self.config_manager)
    
    def create_task_endpoint(self):
        """
        Endpoint for creating new task.
        Requires can_create_tasks permission.
        
        Body: JSON with task data (TaskCreate model)
        
        @return: JSON with created task
        """
        task_data = request.validated_data
        user_info = request.user_info
        
        logging.info(f"Task creation request from user: {user_info['telegram_username']}")
        logging.debug(f"Task data: {task_data.model_dump()}")
        
        # Check if assignee exists
        if task_data.assignee:
            assignee_exists = self.users_manager.find_one(telegram_username=task_data.assignee)
            if not assignee_exists:
                logging.warning(f"Assignee user not found: {task_data.assignee}")
                return generate_response(
                    {'error': f'User {task_data.assignee} not found'},
                    status='error',
                    status_code=400,
                    config_manager=self.config_manager
                )
        
        # Prepare task data for saving to CSV
        task_dict = task_data.model_dump(exclude_unset=True)
        task_dict['creator'] = user_info['telegram_username']
        
        # Generate task_id
        all_tasks = self.tasks_manager.read_all()
        last_id = 0
        for task in all_tasks:
            try:
                task_id = int(task.get('task_id', 0))
                last_id = max(last_id, task_id)
            except:
                pass
        task_dict['task_id'] = last_id + 1
        
        # Convert tags to JSON string
        if task_dict.get('tags'):
            task_dict['tags'] = json.dumps(task_dict['tags'], ensure_ascii=False)
        
        # Create task
        try:
            created_task = self.tasks_manager.insert(task_dict)
            
            # Send WebSocket event
            self.socketio.emit(SystemConstants.WS_EVENTS['TASK_CREATED'], {
                'task': created_task,
                'creator': user_info['telegram_username'],
                'timestamp': datetime.now().isoformat()
            })
            
            logging.info(f"Task #{created_task['task_id']} created by user {user_info['telegram_username']}")
            
            return generate_response({
                'task_id': created_task['task_id'],
                'title': created_task['title'],
                'status': created_task['status'],
                'assignee': created_task.get('assignee', ''),
                'creator': created_task['creator'],
                'created_at': created_task['created_at'],
                'message': 'Task created successfully'
            }, status_code=201, config_manager=self.config_manager)
        
        except Exception as e:
            logging.error(f"Error creating task: {e}")
            return generate_response(
                {'error': str(e)},
                status='error',
                status_code=500,
                config_manager=self.config_manager
            )
    
    def update_task_endpoint(self, task_id: int):
        """
        Endpoint for updating existing task.
        
        Path parameters: task_id - ID of task to update
        Body: JSON with task fields to update (TaskUpdate model)
        
        @return: JSON with update result
        """
        update_data = request.validated_data
        user_info = request.user_info
        
        logging.info(f"Task update request for task #{task_id} from user: {user_info['telegram_username']}")
        logging.debug(f"Update data: {update_data.model_dump()}")
        
        # Find task
        task = self.tasks_manager.find_one(task_id=str(task_id))
        if not task:
            logging.warning(f"Task #{task_id} not found")
            return generate_response(
                {'error': f'Task #{task_id} not found'},
                status='error',
                status_code=404,
                config_manager=self.config_manager
            )
        
        # MODIFICATION: Removed permission check - now everyone can edit any task
        user_telegram = user_info['telegram_username']
        
        # Check if new assignee exists
        if update_data.assignee and update_data.assignee != task.get('assignee'):
            assignee_exists = self.users_manager.find_one(telegram_username=update_data.assignee)
            if not assignee_exists:
                logging.warning(f"Assignee user not found: {update_data.assignee}")
                return generate_response(
                    {'error': f'User {update_data.assignee} not found'},
                    status='error',
                    status_code=400,
                    config_manager=self.config_manager
                )
        
        # Prepare update data
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Handle tags
        if 'tags' in update_dict:
            update_dict['tags'] = json.dumps(update_dict['tags'], ensure_ascii=False)
        
        # Handle task completion
        if update_dict.get('status') == 'done' and task.get('status') != 'done':
            update_dict['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update task
        success = self.tasks_manager.update(
            {'task_id': str(task_id)},
            update_dict
        )
        
        if not success:
            logging.error(f"Error updating task #{task_id}")
            return generate_response(
                {'error': 'Error updating task'},
                status='error',
                status_code=500,
                config_manager=self.config_manager
            )
        
        # Send WebSocket event
        self.socketio.emit(SystemConstants.WS_EVENTS['TASK_UPDATED'], {
            'task_id': task_id,
            'updated_fields': list(update_dict.keys()),
            'updated_by': user_telegram,
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"Task #{task_id} updated by user {user_telegram}")
        return generate_response({
            'task_id': task_id,
            'message': 'Task updated successfully',
            'updated_fields': list(update_dict.keys())
        }, config_manager=self.config_manager)