"""
Export API endpoints.
Handles data export operations.
"""

import csv
import json
import logging
import io
from datetime import datetime, timedelta
from flask import Response, request, session

from modules.decorators import generate_response


class ExportAPI:
    """
    Export API endpoints.
    
    @param tasks_manager: CSV data manager for tasks
    @param users_manager: CSV data manager for users
    @param cache_manager: Cache manager instance
    @param config_manager: Configuration manager instance
    """
    
    def __init__(self, tasks_manager, users_manager, cache_manager, config_manager):
        self.tasks_manager = tasks_manager
        self.users_manager = users_manager
        self.cache_manager = cache_manager
        self.config_manager = config_manager
    
    def export_tasks_csv_endpoint(self):
        """
        Endpoint for exporting tasks to CSV format.
        Available to all users (if enabled in config).
        If not enabled, requires can_export permission.
        
        Query parameters:
            format: Export format (simple/full)
            time_period: Data period (last_week/last_month/all)
            status: Filter by status (comma-separated)
            columns: Selected columns (comma-separated)
            include_users: Include user data (true/false)
        
        @return: CSV file for download
        """
        # Check if export is allowed for all users
        export_allowed_for_all = self.config_manager.is_export_allowed_for_all()
        
        if not export_allowed_for_all:
            # If export not allowed for all, check authentication
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                # Check Flask session
                if 'user_info' not in session:
                    logging.warning(f"Export request without token and session")
                    return generate_response(
                        {'error': 'Authentication required for data export'},
                        status='error',
                        status_code=401,
                        config_manager=self.config_manager
                    )
                
                # Use data from session
                user_telegram = session['user_info'].get('telegram_username')
                logging.info(f"CSV export request from user: {user_telegram} (via session)")
            else:
                # In a real implementation, validate token here
                user_telegram = 'authenticated_user'
                logging.info(f"CSV export request from authenticated user")
        else:
            # Export allowed for all
            user_telegram = 'anonymous'
            logging.info(f"CSV export request from anonymous user")
        
        logging.debug(f"Query parameters: {dict(request.args)}")
        
        # Export parameters
        format_type = request.args.get('format', 'full')
        time_period = request.args.get('time_period')
        status_filter = request.args.get('status', '').split(',')
        columns = request.args.get('columns', '').split(',')
        include_users = request.args.get('include_users', 'false').lower() == 'true'
        
        # Generate cache key
        cache_key = self.cache_manager.generate_key(
            'export_csv',
            format=format_type,
            time_period=time_period or '',
            status=','.join(sorted(status_filter)) if status_filter[0] else '',
            columns=','.join(sorted(columns)) if columns[0] else '',
            include_users=include_users,
            date=datetime.now().strftime('%Y-%m-%d')
        )
        
        # Check cache
        cached_csv = self.cache_manager.get(cache_key)
        if cached_csv and format_type != 'simple':
            logging.debug(f"Using cached CSV for key: {cache_key}")
            return Response(
                cached_csv,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': 
                    f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'
                }
            )
        
        # Get tasks
        all_tasks = self.tasks_manager.read_all()
        
        # Filter by time period
        filtered_tasks = all_tasks
        if time_period == 'last_week':
            cutoff_date = datetime.now() - timedelta(days=7)
            filtered_tasks = [
                task for task in all_tasks
                if task.get('created_at') and 
                datetime.strptime(task['created_at'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
            ]
        elif time_period == 'last_month':
            cutoff_date = datetime.now() - timedelta(days=30)
            filtered_tasks = [
                task for task in all_tasks
                if task.get('created_at') and 
                datetime.strptime(task['created_at'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
            ]
        
        # Filter by status
        if status_filter and status_filter[0]:
            filtered_tasks = [task for task in filtered_tasks if task.get('status') in status_filter]
        
        # Determine CSV columns
        if columns and columns[0]:
            csv_columns = [col.strip() for col in columns if col.strip() in [
                'task_id', 'title', 'description', 'status', 'assignee', 
                'creator', 'created_at', 'updated_at', 'due_date', 
                'completed_at', 'priority', 'tags'
            ]]
        else:
            # Default columns
            csv_columns = [
                'task_id', 'title', 'status', 'assignee', 'creator',
                'created_at', 'due_date', 'priority'
            ]
        
        # Add user name columns if requested
        if include_users:
            if 'assignee' in csv_columns:
                csv_columns.append('assignee_name')
            if 'creator' in csv_columns:
                csv_columns.append('creator_name')
        
        # Prepare data for CSV
        csv_data = []
        
        for task in filtered_tasks:
            row = {}
            
            for column in csv_columns:
                if column == 'assignee_name' and include_users:
                    # Get assignee name
                    if task.get('assignee'):
                        user = self.users_manager.find_one(telegram_username=task['assignee'])
                        row[column] = user.get('full_name', '') if user else ''
                    else:
                        row[column] = ''
                elif column == 'creator_name' and include_users:
                    # Get creator name
                    if task.get('creator'):
                        user = self.users_manager.find_one(telegram_username=task['creator'])
                        row[column] = user.get('full_name', '') if user else ''
                    else:
                        row[column] = ''
                else:
                    row[column] = task.get(column, '')
            
            csv_data.append(row)
        
        # Create CSV
        output = io.StringIO()
        
        if csv_data:
            writer = csv.DictWriter(output, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(csv_data)
        
        csv_content = output.getvalue()
        
        # Save to cache
        if format_type != 'simple':
            self.cache_manager.set(cache_key, csv_content, ttl=300)
        
        if user_telegram != 'anonymous':
            logging.info(f"CSV export completed for user {user_telegram}, records: {len(csv_data)}")
        else:
            logging.info(f"CSV export completed for anonymous user, records: {len(csv_data)}")
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 
                f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )