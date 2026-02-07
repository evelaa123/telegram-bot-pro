"""
Statistics router.
Handles dashboard and analytics endpoints.
"""
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query

from sqlalchemy import select, func, cast, Date, and_

from api.schemas.stats import (
    DashboardStats, StatsResponse, DailyStats, RequestStatsItem,
    TopUser, ChartData, RecentRequest, RecentRequestsResponse,
    CostAnalysis, APIUsageOverview, APIUsageDailySummary, APIUsageMonthlySummary,
    CostAlert, ProviderStats, ModelStats, DailyUsageData
)
from api.services.auth_service import get_current_admin
from database import async_session_maker
from database.models import User, Request, RequestType, VideoTask, VideoTaskStatus, Admin, APIUsageLog, Subscription
from bot.services.usage_tracking_service import usage_tracking_service
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get dashboard statistics.
    """
    async with async_session_maker() as session:
        today = date.today()
        now = datetime.utcnow()
        
        # Active users today
        active_today_result = await session.execute(
            select(func.count(func.distinct(Request.user_id)))
            .where(cast(Request.created_at, Date) == today)
        )
        active_users_today = active_today_result.scalar() or 0
        
        # Total requests today
        requests_today_result = await session.execute(
            select(func.count(Request.id))
            .where(cast(Request.created_at, Date) == today)
        )
        total_requests_today = requests_today_result.scalar() or 0
        
        # Total cost today
        cost_today_result = await session.execute(
            select(func.coalesce(func.sum(Request.cost_usd), 0))
            .where(cast(Request.created_at, Date) == today)
        )
        total_cost_today = float(cost_today_result.scalar() or 0)
        
        # Queue size (pending video tasks)
        queue_result = await session.execute(
            select(func.count(VideoTask.id))
            .where(VideoTask.status.in_([
                VideoTaskStatus.QUEUED,
                VideoTaskStatus.IN_PROGRESS
            ]))
        )
        queue_size = queue_result.scalar() or 0
        
        # Total users
        total_users_result = await session.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0
        
        # Total requests
        total_requests_result = await session.execute(
            select(func.count(Request.id))
        )
        total_requests = total_requests_result.scalar() or 0
        
        # Total cost
        total_cost_result = await session.execute(
            select(func.coalesce(func.sum(Request.cost_usd), 0))
        )
        total_cost = float(total_cost_result.scalar() or 0)
        
        # Hourly activity (last 24 hours)
        hourly_activity = []
        for i in range(24):
            hour_start = now - timedelta(hours=24-i)
            hour_end = now - timedelta(hours=23-i)
            
            count_result = await session.execute(
                select(func.count(Request.id))
                .where(and_(
                    Request.created_at >= hour_start,
                    Request.created_at < hour_end
                ))
            )
            count = count_result.scalar() or 0
            
            hourly_activity.append(ChartData(
                label=hour_start.strftime("%H:00"),
                value=float(count)
            ))
        
        # Requests by type (today)
        requests_by_type = []
        for req_type in RequestType:
            count_result = await session.execute(
                select(func.count(Request.id))
                .where(and_(
                    Request.type == req_type,
                    cast(Request.created_at, Date) == today
                ))
            )
            count = count_result.scalar() or 0
            
            requests_by_type.append(ChartData(
                label=req_type.value.capitalize(),
                value=float(count)
            ))
        
        # Daily costs (last 30 days)
        daily_costs = []
        for i in range(30):
            day = today - timedelta(days=29-i)
            
            cost_result = await session.execute(
                select(func.coalesce(func.sum(Request.cost_usd), 0))
                .where(cast(Request.created_at, Date) == day)
            )
            cost = float(cost_result.scalar() or 0)
            
            daily_costs.append(ChartData(
                label=day.strftime("%m/%d"),
                value=cost
            ))
        
        # Top 10 users
        top_users_result = await session.execute(
            select(
                User.telegram_id,
                User.username,
                User.first_name,
                func.count(Request.id).label('total_requests'),
                func.coalesce(func.sum(Request.cost_usd), 0).label('total_cost')
            )
            .join(Request, Request.user_id == User.id)
            .group_by(User.id)
            .order_by(func.count(Request.id).desc())
            .limit(10)
        )
        
        top_users = [
            TopUser(
                telegram_id=row.telegram_id,
                username=row.username,
                first_name=row.first_name,
                total_requests=row.total_requests,
                total_cost_usd=float(row.total_cost)
            )
            for row in top_users_result
        ]
        
        return DashboardStats(
            active_users_today=active_users_today,
            total_requests_today=total_requests_today,
            total_cost_today_usd=total_cost_today,
            queue_size=queue_size,
            total_users=total_users,
            total_requests=total_requests,
            total_cost_usd=total_cost,
            hourly_activity=hourly_activity,
            requests_by_type=requests_by_type,
            daily_costs=daily_costs,
            top_users=top_users
        )


@router.get("/daily", response_model=StatsResponse)
async def get_daily_stats(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get daily statistics for a date range.
    Defaults to last 30 days.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    async with async_session_maker() as session:
        daily_stats = []
        total_requests = 0
        total_cost = 0.0
        unique_users = set()
        
        current_date = start_date
        while current_date <= end_date:
            # Get stats for this day
            requests_result = await session.execute(
                select(
                    Request.type,
                    func.count(Request.id).label('count'),
                    func.coalesce(func.sum(Request.cost_usd), 0).label('cost')
                )
                .where(cast(Request.created_at, Date) == current_date)
                .group_by(Request.type)
            )
            
            day_requests = list(requests_result)
            day_total = sum(r.count for r in day_requests)
            day_cost = sum(float(r.cost) for r in day_requests)
            
            # Unique users
            users_result = await session.execute(
                select(func.count(func.distinct(Request.user_id)))
                .where(cast(Request.created_at, Date) == current_date)
            )
            day_unique_users = users_result.scalar() or 0
            
            requests_by_type = [
                RequestStatsItem(
                    type=r.type.value,
                    count=r.count,
                    cost_usd=float(r.cost)
                )
                for r in day_requests
            ]
            
            daily_stats.append(DailyStats(
                date=current_date,
                total_requests=day_total,
                unique_users=day_unique_users,
                total_cost_usd=day_cost,
                requests_by_type=requests_by_type
            ))
            
            total_requests += day_total
            total_cost += day_cost
            
            current_date += timedelta(days=1)
        
        # Get overall unique users
        overall_users_result = await session.execute(
            select(func.count(func.distinct(Request.user_id)))
            .where(and_(
                cast(Request.created_at, Date) >= start_date,
                cast(Request.created_at, Date) <= end_date
            ))
        )
        overall_unique_users = overall_users_result.scalar() or 0
        
        return StatsResponse(
            period_start=start_date,
            period_end=end_date,
            total_requests=total_requests,
            unique_users=overall_unique_users,
            total_cost_usd=total_cost,
            daily_stats=daily_stats
        )


@router.get("/recent", response_model=RecentRequestsResponse)
async def get_recent_requests(
    limit: int = Query(20, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get recent requests for live feed.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Request, User)
            .join(User, Request.user_id == User.id)
            .order_by(Request.created_at.desc())
            .limit(limit)
        )
        
        requests = [
            RecentRequest(
                id=req.id,
                user_telegram_id=user.telegram_id,
                username=user.username,
                type=req.type.value,
                prompt_preview=req.prompt[:100] if req.prompt else None,
                status=req.status.value,
                cost_usd=float(req.cost_usd) if req.cost_usd else None,
                created_at=req.created_at
            )
            for req, user in result
        ]
        
        return RecentRequestsResponse(requests=requests)


@router.get("/costs", response_model=CostAnalysis)
async def get_cost_analysis(
    days: int = Query(30, ge=1, le=365),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get cost analysis for the specified period.
    """
    async with async_session_maker() as session:
        start_date = date.today() - timedelta(days=days)
        
        # Total cost
        total_result = await session.execute(
            select(func.coalesce(func.sum(Request.cost_usd), 0))
            .where(cast(Request.created_at, Date) >= start_date)
        )
        total_cost = float(total_result.scalar() or 0)
        
        # Cost by model
        model_result = await session.execute(
            select(
                Request.model,
                func.coalesce(func.sum(Request.cost_usd), 0).label('cost')
            )
            .where(and_(
                cast(Request.created_at, Date) >= start_date,
                Request.model.isnot(None)
            ))
            .group_by(Request.model)
        )
        cost_by_model = {
            row.model: float(row.cost)
            for row in model_result
        }
        
        # Cost by type
        type_result = await session.execute(
            select(
                Request.type,
                func.coalesce(func.sum(Request.cost_usd), 0).label('cost')
            )
            .where(cast(Request.created_at, Date) >= start_date)
            .group_by(Request.type)
        )
        cost_by_type = {
            row.type.value: float(row.cost)
            for row in type_result
        }
        
        # Daily average
        daily_average = total_cost / days if days > 0 else 0
        
        # Monthly projection
        monthly_projection = daily_average * 30
        
        return CostAnalysis(
            total_cost_usd=total_cost,
            cost_by_model=cost_by_model,
            cost_by_type=cost_by_type,
            daily_average_usd=daily_average,
            monthly_projection_usd=monthly_projection
        )


@router.get("/api-usage", response_model=APIUsageOverview)
async def get_api_usage_overview(
    daily_budget_usd: float = Query(10.0, description="Daily budget in USD"),
    monthly_budget_usd: float = Query(200.0, description="Monthly budget in USD"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get comprehensive API usage statistics for monitoring costs.
    Includes daily and monthly summaries with alerts.
    """
    # Get daily summary
    daily_data = await usage_tracking_service.get_daily_summary()
    daily_summary = APIUsageDailySummary(
        date=daily_data["date"],
        total_requests=daily_data["total_requests"],
        total_cost_usd=daily_data["total_cost_usd"],
        total_cost_rub=daily_data["total_cost_rub"],
        error_count=daily_data["error_count"],
        error_rate=daily_data["error_rate"],
        by_provider={
            k: ProviderStats(**v) for k, v in daily_data["by_provider"].items()
        },
        by_model={
            k: ModelStats(**v) for k, v in daily_data["by_model"].items()
        }
    )
    
    # Get monthly summary
    monthly_data = await usage_tracking_service.get_monthly_summary()
    monthly_summary = APIUsageMonthlySummary(
        year=monthly_data["year"],
        month=monthly_data["month"],
        total_requests=monthly_data["total_requests"],
        total_cost_usd=monthly_data["total_cost_usd"],
        total_cost_rub=monthly_data["total_cost_rub"],
        projected_monthly_usd=monthly_data["projected_monthly_usd"],
        projected_monthly_rub=monthly_data["projected_monthly_rub"],
        days_elapsed=monthly_data["days_elapsed"],
        days_in_month=monthly_data["days_in_month"],
        daily_data=[DailyUsageData(**d) for d in monthly_data["daily_data"]],
        by_provider={
            k: ModelStats(**v) for k, v in monthly_data["by_provider"].items()
        }
    )
    
    # Get alerts
    alerts_data = await usage_tracking_service.get_cost_alerts(
        daily_budget_usd=daily_budget_usd,
        monthly_budget_usd=monthly_budget_usd
    )
    alerts = [CostAlert(**a) for a in alerts_data]
    
    return APIUsageOverview(
        daily=daily_summary,
        monthly=monthly_summary,
        alerts=alerts
    )


@router.get("/api-usage/daily")
async def get_api_usage_daily(
    target_date: date = Query(default=None, description="Date to get stats for (default: today)"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get daily API usage breakdown.
    """
    return await usage_tracking_service.get_daily_summary(target_date)


@router.get("/api-usage/monthly")
async def get_api_usage_monthly(
    year: int = Query(default=None, description="Year (default: current)"),
    month: int = Query(default=None, ge=1, le=12, description="Month (default: current)"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get monthly API usage summary.
    """
    return await usage_tracking_service.get_monthly_summary(year, month)


@router.get("/api-usage/alerts")
async def get_api_usage_alerts(
    daily_budget_usd: float = Query(10.0, description="Daily budget in USD"),
    monthly_budget_usd: float = Query(200.0, description="Monthly budget in USD"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get cost alerts based on configured budgets.
    """
    return await usage_tracking_service.get_cost_alerts(
        daily_budget_usd=daily_budget_usd,
        monthly_budget_usd=monthly_budget_usd
    )


@router.get("/api-usage/user/{user_id}")
async def get_api_usage_by_user(
    user_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get API usage for a specific user.
    """
    return await usage_tracking_service.get_usage_by_user(user_id, days)


@router.get("/subscriptions/monthly")
async def get_monthly_subscriptions(
    year: int = Query(default=None, description="Year (default: current)"),
    month: int = Query(default=None, ge=1, le=12, description="Month (default: current)"),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get subscriptions purchased in a given month.
    """
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    target_year = year or now.year
    target_month = month or now.month
    
    # Calculate month boundaries
    month_start = datetime(target_year, target_month, 1, tzinfo=tz.utc)
    if target_month == 12:
        month_end = datetime(target_year + 1, 1, 1, tzinfo=tz.utc)
    else:
        month_end = datetime(target_year, target_month + 1, 1, tzinfo=tz.utc)
    
    async with async_session_maker() as session:
        # Get subscriptions in the period
        result = await session.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(and_(
                Subscription.created_at >= month_start,
                Subscription.created_at < month_end
            ))
            .order_by(Subscription.created_at.desc())
        )
        
        subscriptions = []
        total_revenue_rub = 0.0
        
        for sub, user in result:
            total_revenue_rub += float(sub.amount_rub)
            subscriptions.append({
                "id": sub.id,
                "user_id": sub.user_id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "payment_id": sub.payment_id,
                "payment_provider": sub.payment_provider,
                "amount_rub": float(sub.amount_rub),
                "starts_at": sub.starts_at.isoformat() if sub.starts_at else None,
                "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                "is_active": sub.is_active,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
            })
        
        # Count active premium users
        active_premium_result = await session.execute(
            select(func.count(User.id))
            .where(and_(
                User.subscription_type == "premium",
                User.subscription_expires_at > now
            ))
        )
        active_premium_count = active_premium_result.scalar() or 0
        
        return {
            "year": target_year,
            "month": target_month,
            "total_subscriptions": len(subscriptions),
            "total_revenue_rub": total_revenue_rub,
            "active_premium_users": active_premium_count,
            "subscriptions": subscriptions
        }
