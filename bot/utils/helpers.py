"""
Helper utilities for the bot.
"""
import html
from typing import Union


def format_number(num: Union[int, float], precision: int = 2) -> str:
    """
    Format number with thousand separators.
    
    Args:
        num: Number to format
        precision: Decimal precision for floats
        
    Returns:
        Formatted string
    """
    if isinstance(num, float):
        return f"{num:,.{precision}f}"
    return f"{num:,}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for Telegram HTML parse mode.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    return html.escape(text)


def format_duration(seconds: int) -> str:
    """
    Format duration in human readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "2h 30m" or "45s"
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string like "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}" if unit != 'B' else f"{bytes_size} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def format_cost(cost_usd: float) -> str:
    """
    Format cost in USD with appropriate precision.
    
    Args:
        cost_usd: Cost in USD
        
    Returns:
        Formatted string
    """
    if cost_usd < 0.01:
        return f"${cost_usd:.6f}"
    elif cost_usd < 1:
        return f"${cost_usd:.4f}"
    else:
        return f"${cost_usd:.2f}"
