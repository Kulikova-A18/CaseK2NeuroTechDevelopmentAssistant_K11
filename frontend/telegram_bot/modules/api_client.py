"""
API client for interaction with server REST API.
"""

import logging
import aiohttp
from typing import Optional, Dict, Any, List
from modules.constants import BotConstants

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interaction with server API."""
    
    def __init__(self, base_url: str = BotConstants.API_BASE_URL):
        """
        Initialize API client.
        
        @param base_url: Base URL of API server
        """
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        """Enter async context manager."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self, token: str = None) -> Dict[str, str]:
        """
        Get headers for request.
        
        @param token: Authentication token
        @return: Dictionary with headers
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TelegramTaskBot/1.0'
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers
    
    async def authenticate(self, telegram_username: str, full_name: str = None) -> Dict[str, Any]:
        """
        Authenticate user via Telegram username.
        
        @param telegram_username: User's Telegram username
        @param full_name: User's full name
        @return: Authentication result with user info and token
        """
        url = f"{self.base_url}/api/telegram/auth"
        data = {
            'telegram_username': telegram_username,
            'full_name': full_name
        }
        
        try:
            async with self.session.post(url, json=data, headers=self._get_headers()) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {})
                elif response.status == 404:
                    logger.warning(f"User {telegram_username} not found in system")
                    return {}
                else:
                    logger.error(f"Authentication error: {response.status}")
                    return {}
        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {e}")
            return {}
    
    async def get_tasks(self, token: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get list of tasks.
        
        @param token: Authentication token
        @param filters: Dictionary with filter parameters
        @return: List of tasks
        """
        url = f"{self.base_url}/api/tasks"
        
        # Prepare request parameters
        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    params[key] = ','.join(value)
                else:
                    params[key] = value
        
        try:
            async with self.session.get(url, params=params, headers=self._get_headers(token)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {}).get('tasks', [])
                elif response.status == 401:
                    logger.error("Token expired or invalid")
                    return []
                else:
                    logger.error(f"Error getting tasks: {response.status}")
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {e}")
            return []
    
    async def create_task(self, token: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create new task.
        
        @param token: Authentication token
        @param task_data: Task data dictionary
        @return: Created task data or None
        """
        url = f"{self.base_url}/api/tasks"
        
        async with self.session.post(url, json=task_data, headers=self._get_headers(token)) as response:
            if response.status == 201:
                result = await response.json()
                return result.get('data', {})
            else:
                error_text = await response.text()
                logger.error(f"Error creating task: {response.status}, {error_text}")
                return None
    
    async def update_task(self, token: str, task_id: int, update_data: dict) -> dict:
        """
        Update task by ID.
        
        @param token: Access token
        @param task_id: Task ID
        @param update_data: Data to update
        @return: Response dict with success/error info
        """
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.put(
                    f'{self.base_url}/api/tasks/{task_id}',
                    json=update_data
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except:
                            # Если ответ не в формате JSON, возвращаем успех
                            return {'success': True, 'message': 'Task updated successfully'}
                    else:
                        error_text = await response.text()
                        try:
                            error_json = await response.json()
                            return {'error': error_json.get('error', error_text)}
                        except:
                            return {'error': f'HTTP {response.status}: {error_text}'}
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return {'error': str(e)}
    
    async def get_llm_analysis(self, token: str, analysis_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get AI analysis of tasks.
        
        @param token: Authentication token
        @param analysis_params: Analysis parameters
        @return: Analysis results or None
        """
        url = f"{self.base_url}/api/llm/analyze/tasks"
        
        async with self.session.post(url, json=analysis_params, headers=self._get_headers(token)) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                logger.error(f"Error getting analysis: {response.status}")
                return None
    
    async def export_tasks_csv(self, token: str, params: Dict[str, Any] = None) -> Optional[bytes]:
        """
        Export tasks to CSV.
        
        @param token: Authentication token
        @param params: Export parameters
        @return: CSV file bytes or None
        """
        url = f"{self.base_url}/api/export/tasks.csv"
        
        # Prepare query parameters
        query_params = params or {}
        
        async with self.session.get(url, params=query_params, headers=self._get_headers(token)) as response:
            if response.status == 200:
                return await response.read()
            else:
                logger.error(f"Export error: {response.status}")
                return None
    
    async def create_user(self, token: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create new user.
        
        @param token: Authentication token
        @param user_data: User data
        @return: Created user data or None
        """
        url = f"{self.base_url}/api/users"
        
        async with self.session.post(url, json=user_data, headers=self._get_headers(token)) as response:
            if response.status == 201:
                result = await response.json()
                return result.get('data', {})
            else:
                logger.error(f"Error creating user: {response.status}")
                return None
    
    async def get_system_health(self) -> Optional[Dict[str, Any]]:
        """
        Get system health status.
        
        @return: System health data or None
        """
        url = f"{self.base_url}/api/health"
        
        try:
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {})
                else:
                    logger.error(f"Health check error: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"API unavailable: {e}")
            return None
        
async def update_task(self, token: str, task_id: int, update_data: dict) -> dict:
    """
    Update task by ID.
    
    @param token: Access token
    @param task_id: Task ID
    @param update_data: Data to update
    @return: Response dict
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.put(
                f'{self.base_url}/api/tasks/{task_id}',
                json=update_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {'error': f'HTTP {response.status}: {error_text}'}
    except Exception as e:
        return {'error': str(e)}