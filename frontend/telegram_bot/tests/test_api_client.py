"""
Tests for API client module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from modules.api_client import APIClient
from modules.constants import BotConstants


@pytest.fixture
def api_client():
    """Create API client fixture."""
    return APIClient(base_url="http://test-api.com")


@pytest.mark.asyncio
async def test_authenticate_success(api_client):
    """Test successful authentication."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        'data': {
            'authenticated': True,
            'access_token': 'test_token',
            'user': {'id': 1, 'telegram_username': '@test'}
        }
    }
    
    with patch('aiohttp.ClientSession.post', return_value=mock_response):
        async with api_client:
            result = await api_client.authenticate('@test', 'Test User')
            
            assert result['authenticated'] is True
            assert result['access_token'] == 'test_token'
            assert result['user']['telegram_username'] == '@test'


@pytest.mark.asyncio
async def test_authenticate_user_not_found(api_client):
    """Test authentication when user not found."""
    mock_response = AsyncMock()
    mock_response.status = 404
    
    with patch('aiohttp.ClientSession.post', return_value=mock_response):
        async with api_client:
            result = await api_client.authenticate('@nonexistent')
            assert result == {}


@pytest.mark.asyncio
async def test_get_tasks_success(api_client):
    """Test successful task retrieval."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        'data': {
            'tasks': [
                {'id': 1, 'title': 'Test Task', 'status': 'todo'},
                {'id': 2, 'title': 'Another Task', 'status': 'in_progress'}
            ]
        }
    }
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        async with api_client:
            tasks = await api_client.get_tasks('test_token', {'status': 'todo'})
            
            assert len(tasks) == 2
            assert tasks[0]['title'] == 'Test Task'
            assert tasks[1]['status'] == 'in_progress'


@pytest.mark.asyncio
async def test_get_tasks_unauthorized(api_client):
    """Test task retrieval with invalid token."""
    mock_response = AsyncMock()
    mock_response.status = 401
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        async with api_client:
            tasks = await api_client.get_tasks('invalid_token')
            assert tasks == []


@pytest.mark.asyncio
async def test_create_task_success(api_client):
    """Test successful task creation."""
    mock_response = AsyncMock()
    mock_response.status = 201
    mock_response.json.return_value = {
        'data': {'id': 123, 'title': 'New Task', 'status': 'todo'}
    }
    
    task_data = {'title': 'New Task', 'description': 'Test description'}
    
    with patch('aiohttp.ClientSession.post', return_value=mock_response):
        async with api_client:
            result = await api_client.create_task('test_token', task_data)
            
            assert result['id'] == 123
            assert result['title'] == 'New Task'
            assert result['status'] == 'todo'


@pytest.mark.asyncio
async def test_update_task_success(api_client):
    """Test successful task update."""
    mock_response = AsyncMock()
    mock_response.status = 200
    
    update_data = {'status': 'done'}
    
    with patch('aiohttp.ClientSession.put', return_value=mock_response):
        async with api_client:
            result = await api_client.update_task('test_token', 123, update_data)
            assert result is True


@pytest.mark.asyncio
async def test_export_tasks_csv_success(api_client):
    """Test successful CSV export."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b'task_id,title,status\n1,Test,todo'
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        async with api_client:
            csv_data = await api_client.export_tasks_csv('test_token')
            
            assert csv_data == b'task_id,title,status\n1,Test,todo'
            assert isinstance(csv_data, bytes)


@pytest.mark.asyncio
async def test_get_system_health_success(api_client):
    """Test successful system health check."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        'data': {
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z'
        }
    }
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        async with api_client:
            health = await api_client.get_system_health()
            
            assert health['status'] == 'healthy'
            assert 'timestamp' in health


@pytest.mark.asyncio
async def test_get_system_health_unavailable(api_client):
    """Test system health check when API is unavailable."""
    with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientError("Connection failed")):
        async with api_client:
            health = await api_client.get_system_health()
            assert health is None