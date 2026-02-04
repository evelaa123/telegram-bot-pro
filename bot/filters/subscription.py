"""
Subscription filter for checking channel membership.
"""
from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.services.subscription_service import SubscriptionService


class SubscriptionFilter(BaseFilter):
    """
    Filter that checks if user is subscribed to the channel.
    """
    
    def __init__(self, require_subscription: bool = True):
        """
        Initialize filter.
        
        Args:
            require_subscription: If True, only subscribed users pass
        """
        self.require_subscription = require_subscription
    
    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        subscription_service: SubscriptionService
    ) -> bool:
        """
        Check if user passes the filter.
        
        Args:
            event: Message or CallbackQuery
            subscription_service: Subscription service instance
            
        Returns:
            True if user passes filter
        """
        user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return not self.require_subscription
        
        is_subscribed = await subscription_service.check_subscription(user_id)
        
        if self.require_subscription:
            return is_subscribed
        else:
            return not is_subscribed
