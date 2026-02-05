"""
API usage tracking service.
Tracks all API calls for cost monitoring and analytics.
"""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker
from database.models import APIUsageLog
from config import settings
import structlog

logger = structlog.get_logger()


class UsageTrackingService:
    """
    Service for tracking API usage and costs.
    Provides analytics for monitoring expenses.
    """
    
    async def log_api_call(
        self,
        provider: str,
        model: str,
        endpoint: str,
        input_tokens: int = None,
        output_tokens: int = None,
        cost_usd: Decimal = None,
        cost_rub: Decimal = None,
        duration_ms: int = None,
        success: bool = True,
        error_message: str = None,
        user_id: int = None
    ) -> int:
        """
        Log an API call for tracking.
        
        Args:
            provider: API provider (cometapi, gigachat, openai)
            model: Model name used
            endpoint: API endpoint (chat, image, video, audio)
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            cost_usd: Cost in USD
            cost_rub: Cost in RUB
            duration_ms: Response time in milliseconds
            success: Whether the call was successful
            error_message: Error message if failed
            user_id: Database user ID (optional)
            
        Returns:
            Log entry ID
        """
        async with async_session_maker() as session:
            log_entry = APIUsageLog(
                user_id=user_id,
                provider=provider,
                model=model,
                endpoint=endpoint,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                cost_rub=cost_rub,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message
            )
            
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            
            return log_entry.id
    
    async def get_daily_summary(
        self,
        target_date: date = None
    ) -> Dict[str, Any]:
        """
        Get daily usage summary.
        
        Args:
            target_date: Date to get summary for (default: today)
            
        Returns:
            Dict with usage statistics
        """
        if target_date is None:
            target_date = date.today()
        
        start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)
        
        async with async_session_maker() as session:
            # Get totals by provider
            result = await session.execute(
                select(
                    APIUsageLog.provider,
                    func.count(APIUsageLog.id).label('count'),
                    func.sum(APIUsageLog.input_tokens).label('input_tokens'),
                    func.sum(APIUsageLog.output_tokens).label('output_tokens'),
                    func.sum(APIUsageLog.cost_usd).label('cost_usd'),
                    func.sum(APIUsageLog.cost_rub).label('cost_rub'),
                    func.avg(APIUsageLog.duration_ms).label('avg_duration')
                )
                .where(and_(
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at < end_dt
                ))
                .group_by(APIUsageLog.provider)
            )
            
            providers = {}
            total_cost_usd = Decimal("0")
            total_cost_rub = Decimal("0")
            total_requests = 0
            
            for row in result:
                providers[row.provider] = {
                    "requests": row.count,
                    "input_tokens": row.input_tokens or 0,
                    "output_tokens": row.output_tokens or 0,
                    "cost_usd": float(row.cost_usd or 0),
                    "cost_rub": float(row.cost_rub or 0),
                    "avg_duration_ms": float(row.avg_duration or 0)
                }
                total_cost_usd += row.cost_usd or Decimal("0")
                total_cost_rub += row.cost_rub or Decimal("0")
                total_requests += row.count
            
            # Get totals by model
            result = await session.execute(
                select(
                    APIUsageLog.model,
                    func.count(APIUsageLog.id).label('count'),
                    func.sum(APIUsageLog.cost_usd).label('cost_usd')
                )
                .where(and_(
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at < end_dt
                ))
                .group_by(APIUsageLog.model)
            )
            
            models = {}
            for row in result:
                models[row.model] = {
                    "requests": row.count,
                    "cost_usd": float(row.cost_usd or 0)
                }
            
            # Get error count
            error_result = await session.execute(
                select(func.count(APIUsageLog.id))
                .where(and_(
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at < end_dt,
                    APIUsageLog.success == False
                ))
            )
            error_count = error_result.scalar() or 0
            
            return {
                "date": target_date.isoformat(),
                "total_requests": total_requests,
                "total_cost_usd": float(total_cost_usd),
                "total_cost_rub": float(total_cost_rub),
                "error_count": error_count,
                "error_rate": (error_count / total_requests * 100) if total_requests > 0 else 0,
                "by_provider": providers,
                "by_model": models
            }
    
    async def get_monthly_summary(
        self,
        year: int = None,
        month: int = None
    ) -> Dict[str, Any]:
        """
        Get monthly usage summary.
        
        Args:
            year: Year (default: current)
            month: Month (default: current)
            
        Returns:
            Dict with monthly statistics
        """
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        async with async_session_maker() as session:
            # Get daily totals
            result = await session.execute(
                select(
                    func.date(APIUsageLog.created_at).label('day'),
                    func.count(APIUsageLog.id).label('count'),
                    func.sum(APIUsageLog.cost_usd).label('cost_usd'),
                    func.sum(APIUsageLog.cost_rub).label('cost_rub')
                )
                .where(and_(
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at < end_dt
                ))
                .group_by(func.date(APIUsageLog.created_at))
                .order_by(func.date(APIUsageLog.created_at))
            )
            
            daily_data = []
            total_cost_usd = Decimal("0")
            total_cost_rub = Decimal("0")
            total_requests = 0
            
            for row in result:
                daily_data.append({
                    "date": row.day.isoformat() if row.day else None,
                    "requests": row.count,
                    "cost_usd": float(row.cost_usd or 0),
                    "cost_rub": float(row.cost_rub or 0)
                })
                total_cost_usd += row.cost_usd or Decimal("0")
                total_cost_rub += row.cost_rub or Decimal("0")
                total_requests += row.count
            
            # Get provider breakdown
            provider_result = await session.execute(
                select(
                    APIUsageLog.provider,
                    func.count(APIUsageLog.id).label('count'),
                    func.sum(APIUsageLog.cost_usd).label('cost_usd')
                )
                .where(and_(
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at < end_dt
                ))
                .group_by(APIUsageLog.provider)
            )
            
            providers = {}
            for row in provider_result:
                providers[row.provider] = {
                    "requests": row.count,
                    "cost_usd": float(row.cost_usd or 0)
                }
            
            # Calculate projections
            days_in_month = (end_dt - start_dt).days
            days_elapsed = (now - start_dt).days + 1
            
            if days_elapsed > 0:
                projected_monthly_usd = float(total_cost_usd) / days_elapsed * days_in_month
                projected_monthly_rub = float(total_cost_rub) / days_elapsed * days_in_month
            else:
                projected_monthly_usd = 0
                projected_monthly_rub = 0
            
            return {
                "year": year,
                "month": month,
                "total_requests": total_requests,
                "total_cost_usd": float(total_cost_usd),
                "total_cost_rub": float(total_cost_rub),
                "projected_monthly_usd": round(projected_monthly_usd, 2),
                "projected_monthly_rub": round(projected_monthly_rub, 2),
                "days_elapsed": days_elapsed,
                "days_in_month": days_in_month,
                "daily_data": daily_data,
                "by_provider": providers
            }
    
    async def get_cost_alerts(
        self,
        daily_budget_usd: float = 10.0,
        monthly_budget_usd: float = 200.0
    ) -> List[Dict[str, Any]]:
        """
        Check for cost alerts based on budgets.
        
        Args:
            daily_budget_usd: Daily budget threshold in USD
            monthly_budget_usd: Monthly budget threshold in USD
            
        Returns:
            List of alert dicts
        """
        alerts = []
        
        # Check daily
        daily = await self.get_daily_summary()
        if daily["total_cost_usd"] > daily_budget_usd:
            alerts.append({
                "type": "daily_over_budget",
                "severity": "high",
                "message": f"Daily costs (${daily['total_cost_usd']:.2f}) exceed budget (${daily_budget_usd})",
                "current": daily["total_cost_usd"],
                "budget": daily_budget_usd
            })
        elif daily["total_cost_usd"] > daily_budget_usd * 0.8:
            alerts.append({
                "type": "daily_warning",
                "severity": "medium",
                "message": f"Daily costs approaching budget: ${daily['total_cost_usd']:.2f} / ${daily_budget_usd}",
                "current": daily["total_cost_usd"],
                "budget": daily_budget_usd
            })
        
        # Check monthly
        monthly = await self.get_monthly_summary()
        if monthly["total_cost_usd"] > monthly_budget_usd:
            alerts.append({
                "type": "monthly_over_budget",
                "severity": "critical",
                "message": f"Monthly costs (${monthly['total_cost_usd']:.2f}) exceed budget (${monthly_budget_usd})",
                "current": monthly["total_cost_usd"],
                "budget": monthly_budget_usd
            })
        elif monthly["projected_monthly_usd"] > monthly_budget_usd:
            alerts.append({
                "type": "monthly_projection_warning",
                "severity": "high",
                "message": f"Projected monthly costs (${monthly['projected_monthly_usd']:.2f}) exceed budget",
                "current": monthly["total_cost_usd"],
                "projected": monthly["projected_monthly_usd"],
                "budget": monthly_budget_usd
            })
        
        # Check error rate
        if daily["error_rate"] > 5:
            alerts.append({
                "type": "high_error_rate",
                "severity": "medium",
                "message": f"High error rate: {daily['error_rate']:.1f}%",
                "error_rate": daily["error_rate"]
            })
        
        return alerts
    
    async def get_usage_by_user(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user.
        
        Args:
            user_id: Database user ID
            days: Number of days to look back
            
        Returns:
            Dict with user's usage statistics
        """
        start_dt = datetime.now(timezone.utc) - timedelta(days=days)
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(
                    APIUsageLog.endpoint,
                    func.count(APIUsageLog.id).label('count'),
                    func.sum(APIUsageLog.cost_usd).label('cost_usd')
                )
                .where(and_(
                    APIUsageLog.user_id == user_id,
                    APIUsageLog.created_at >= start_dt
                ))
                .group_by(APIUsageLog.endpoint)
            )
            
            by_endpoint = {}
            total_cost_usd = Decimal("0")
            total_requests = 0
            
            for row in result:
                by_endpoint[row.endpoint] = {
                    "requests": row.count,
                    "cost_usd": float(row.cost_usd or 0)
                }
                total_cost_usd += row.cost_usd or Decimal("0")
                total_requests += row.count
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_requests": total_requests,
                "total_cost_usd": float(total_cost_usd),
                "by_endpoint": by_endpoint
            }


# Global service instance
usage_tracking_service = UsageTrackingService()
