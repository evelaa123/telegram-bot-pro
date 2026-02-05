"""Statistics schemas."""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class RequestStatsItem(BaseModel):
    """Single request type statistics."""
    type: str
    count: int
    cost_usd: float


class DailyStats(BaseModel):
    """Daily statistics."""
    date: date
    total_requests: int
    unique_users: int
    total_cost_usd: float
    requests_by_type: List[RequestStatsItem]


class TopUser(BaseModel):
    """Top user statistics."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    total_requests: int
    total_cost_usd: float


class ChartData(BaseModel):
    """Chart data point."""
    label: str
    value: float


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    # Today's metrics
    active_users_today: int
    total_requests_today: int
    total_cost_today_usd: float
    queue_size: int
    
    # Totals
    total_users: int
    total_requests: int
    total_cost_usd: float
    
    # Charts data
    hourly_activity: List[ChartData]
    requests_by_type: List[ChartData]
    daily_costs: List[ChartData]
    top_users: List[TopUser]


class StatsResponse(BaseModel):
    """General statistics response."""
    period_start: date
    period_end: date
    total_requests: int
    unique_users: int
    total_cost_usd: float
    daily_stats: List[DailyStats]


class RecentRequest(BaseModel):
    """Recent request for live feed."""
    id: int
    user_telegram_id: int
    username: Optional[str] = None
    type: str
    prompt_preview: Optional[str] = None
    status: str
    cost_usd: Optional[float] = None
    created_at: datetime


class RecentRequestsResponse(BaseModel):
    """Recent requests response."""
    requests: List[RecentRequest]


class CostAnalysis(BaseModel):
    """Cost analysis statistics."""
    total_cost_usd: float
    cost_by_model: Dict[str, float]
    cost_by_type: Dict[str, float]
    daily_average_usd: float
    monthly_projection_usd: float


# API Usage Tracking Schemas
class ProviderStats(BaseModel):
    """Statistics for a single provider."""
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_rub: float
    avg_duration_ms: float


class ModelStats(BaseModel):
    """Statistics for a single model."""
    requests: int
    cost_usd: float


class DailyUsageData(BaseModel):
    """Daily usage data point."""
    date: str
    requests: int
    cost_usd: float
    cost_rub: float


class APIUsageDailySummary(BaseModel):
    """Daily API usage summary."""
    date: str
    total_requests: int
    total_cost_usd: float
    total_cost_rub: float
    error_count: int
    error_rate: float
    by_provider: Dict[str, ProviderStats]
    by_model: Dict[str, ModelStats]


class APIUsageMonthlySummary(BaseModel):
    """Monthly API usage summary."""
    year: int
    month: int
    total_requests: int
    total_cost_usd: float
    total_cost_rub: float
    projected_monthly_usd: float
    projected_monthly_rub: float
    days_elapsed: int
    days_in_month: int
    daily_data: List[DailyUsageData]
    by_provider: Dict[str, ModelStats]


class CostAlert(BaseModel):
    """Cost alert."""
    type: str
    severity: str
    message: str
    current: Optional[float] = None
    projected: Optional[float] = None
    budget: Optional[float] = None
    error_rate: Optional[float] = None


class APIUsageOverview(BaseModel):
    """API usage overview for admin dashboard."""
    daily: APIUsageDailySummary
    monthly: APIUsageMonthlySummary
    alerts: List[CostAlert]
