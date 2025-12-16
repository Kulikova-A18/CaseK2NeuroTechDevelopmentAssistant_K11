"""
Pydantic models for data validation.
Contains all request/response models for API endpoints.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from modules.constants import SystemConstants


class UserBase(BaseModel):
    """Base user model."""
    model_config = ConfigDict(from_attributes=True)

    telegram_username: str = Field(..., min_length=5, max_length=32, pattern=r'^@\w+$')
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default='member')
    is_active: bool = Field(default=True)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    department: Optional[str] = Field(None, max_length=50)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        if v not in SystemConstants.ROLES:
            raise ValueError(f'Role must be one of: {", ".join(SystemConstants.ROLES)}')
        return v


class UserCreate(UserBase):
    """Model for creating a user."""
    pass


class UserResponse(UserBase):
    """User response model."""
    registered_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class TaskBase(BaseModel):
    """Base task model."""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: str = Field(default='todo')
    assignee: Optional[str] = Field(None, pattern=r'^@\w+$')
    priority: str = Field(default='medium')
    due_date: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list, max_length=10)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate task status."""
        if v not in SystemConstants.TASK_STATUSES:
            raise ValueError(f'Status must be one of: {", ".join(SystemConstants.TASK_STATUSES)}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Validate task priority."""
        if v not in SystemConstants.TASK_PRIORITIES:
            raise ValueError(f'Priority must be one of: {", ".join(SystemConstants.TASK_PRIORITIES)}')
        return v

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate due date format."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date format must be YYYY-MM-DD')
        return v


class TaskCreate(TaskBase):
    """Model for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Model for updating a task."""
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    assignee: Optional[str] = Field(None, pattern=r'^@\w+$')
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_length=10)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate task status."""
        if v and v not in SystemConstants.TASK_STATUSES:
            raise ValueError(f'Status must be one of: {", ".join(SystemConstants.TASK_STATUSES)}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Validate task priority."""
        if v and v not in SystemConstants.TASK_PRIORITIES:
            raise ValueError(f'Priority must be one of: {", ".join(SystemConstants.TASK_PRIORITIES)}')
        return v

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate due date format."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date format must be YYYY-MM-DD')
        return v


class TaskResponse(TaskBase):
    """Task response model."""
    task_id: int
    creator: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assignee_name: Optional[str] = None
    creator_name: Optional[str] = None
    is_overdue: Optional[bool] = None
    days_remaining: Optional[int] = None


class AuthRequest(BaseModel):
    """Authentication request model."""
    model_config = ConfigDict(from_attributes=True)

    telegram_username: str = Field(..., min_length=5, max_length=32, pattern=r'^@\w+$')
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)


class AuthResponse(BaseModel):
    """Authentication response model."""
    model_config = ConfigDict(from_attributes=True)

    authenticated: bool
    user: UserResponse
    session_token: str
    refresh_token: str
    permissions: Dict[str, Any]
    expires_in: int  # Token lifetime in seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class LLMAnalysisRequest(BaseModel):
    """LLM analysis request model."""
    model_config = ConfigDict(from_attributes=True)

    time_period: str = Field(default='last_week')
    metrics: List[str] = Field(default=['productivity', 'bottlenecks'])
    format: str = Field(default='json')
    include_recommendations: bool = Field(default=True)
    custom_start: Optional[str] = None
    custom_end: Optional[str] = None

    @field_validator('time_period')
    @classmethod
    def validate_time_period(cls, v):
        """Validate time period."""
        if v not in SystemConstants.TIME_PERIODS:
            raise ValueError(f'Time period must be one of: {", ".join(SystemConstants.TIME_PERIODS)}')
        return v

    @field_validator('metrics')
    @classmethod
    def validate_metrics(cls, v):
        """Validate analysis metrics."""
        for metric in v:
            if metric not in SystemConstants.LLM_METRICS:
                raise ValueError(f'Metric must be one of: {", ".join(SystemConstants.LLM_METRICS)}')
        return v

    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate response format."""
        if v not in ['json', 'markdown']:
            raise ValueError('Format must be json or markdown')
        return v