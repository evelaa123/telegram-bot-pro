"""
Admin filter for checking admin privileges.
"""
from typing import Union, List, Optional

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import settings


class AdminFilter(BaseFilter):
    """
    Filter that checks if user is an admin.
    """
    
    # List of admin user IDs (can be configured via settings or database)
    ADMIN_IDS: List[int] = []
    
    def __init__(self, require_admin: bool = True):
        """
        Initialize filter.
        
        Args:
            require_admin: If True, only admins pass
        """
        self.require_admin = require_admin
    
    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        admin_ids: Optional[List[int]] = None
    ) -> bool:
        """
        Check if user passes the filter.
        
        Args:
            event: Message or CallbackQuery
            admin_ids: Optional list of admin IDs (injected via middleware)
            
        Returns:
            True if user passes filter
        """
        user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return not self.require_admin
        
        # Check against provided admin_ids or class attribute
        admins = admin_ids or self.ADMIN_IDS
        is_admin = user_id in admins
        
        if self.require_admin:
            return is_admin
        else:
            return not is_admin


class ChatTypeFilter(BaseFilter):
    """
    Filter by chat type (private, group, supergroup, channel).
    """
    
    def __init__(self, chat_types: Union[str, List[str]]):
        """
        Initialize filter.
        
        Args:
            chat_types: Allowed chat type(s)
        """
        if isinstance(chat_types, str):
            self.chat_types = [chat_types]
        else:
            self.chat_types = chat_types
    
    async def __call__(self, message: Message) -> bool:
        """
        Check if message is from allowed chat type.
        
        Args:
            message: Message to check
            
        Returns:
            True if chat type is allowed
        """
        return message.chat.type in self.chat_types


class StateFilter(BaseFilter):
    """
    Filter by FSM state.
    """
    
    def __init__(self, states: Union[str, List[str], None] = None):
        """
        Initialize filter.
        
        Args:
            states: Allowed state(s), None for any state
        """
        if states is None:
            self.states = None
        elif isinstance(states, str):
            self.states = [states]
        else:
            self.states = states
    
    async def __call__(self, message: Message, state: str = None) -> bool:
        """
        Check if current state matches.
        
        Args:
            message: Message
            state: Current FSM state
            
        Returns:
            True if state matches
        """
        if self.states is None:
            return True
        return state in self.states
