"""
Input validation utilities for the bot.
"""
import re
from typing import Tuple, Optional


def validate_prompt(
    prompt: str,
    max_length: int = 4000,
    min_length: int = 3
) -> Tuple[bool, Optional[str]]:
    """
    Validate prompt text for AI generation.
    
    Args:
        prompt: Input prompt
        max_length: Maximum allowed length
        min_length: Minimum required length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not prompt or not prompt.strip():
        return False, "Промпт не может быть пустым"
    
    prompt = prompt.strip()
    
    if len(prompt) < min_length:
        return False, f"Промпт слишком короткий (минимум {min_length} символов)"
    
    if len(prompt) > max_length:
        return False, f"Промпт слишком длинный (максимум {max_length} символов)"
    
    return True, None


def validate_video_prompt(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Validate prompt for video generation.
    Checks for prohibited content.
    
    Args:
        prompt: Video prompt
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation
    is_valid, error = validate_prompt(prompt, max_length=2000)
    if not is_valid:
        return is_valid, error
    
    prompt_lower = prompt.lower()
    
    # Check for prohibited content (examples)
    prohibited_patterns = [
        r'\b(nude|naked|nsfw|porn|xxx)\b',
        r'\b(violence|gore|blood|murder)\b',
        r'\b(drugs|cocaine|heroin)\b',
        # Add real person/copyright checks as needed
    ]
    
    for pattern in prohibited_patterns:
        if re.search(pattern, prompt_lower):
            return False, "Промпт содержит запрещённый контент"
    
    return True, None


def validate_image_size(size: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image size for DALL-E 3.
    
    Args:
        size: Size string like "1024x1024"
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_sizes = {"1024x1024", "1792x1024", "1024x1792"}
    
    if size not in valid_sizes:
        return False, f"Неверный размер. Допустимые: {', '.join(valid_sizes)}"
    
    return True, None


def validate_image_style(style: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image style for DALL-E 3.
    
    Args:
        style: Style string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_styles = {"vivid", "natural"}
    
    if style not in valid_styles:
        return False, f"Неверный стиль. Допустимые: {', '.join(valid_styles)}"
    
    return True, None


def validate_video_duration(duration: int) -> Tuple[bool, Optional[str]]:
    """
    Validate video duration for Sora.
    
    Args:
        duration: Duration in seconds
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_durations = {5, 10}
    
    if duration not in valid_durations:
        return False, f"Неверная длительность. Допустимые: {', '.join(map(str, valid_durations))} секунд"
    
    return True, None


def validate_video_model(model: str) -> Tuple[bool, Optional[str]]:
    """
    Validate video model name.
    
    Args:
        model: Model name
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_models = {"sora-2", "sora-2-pro"}
    
    if model not in valid_models:
        return False, f"Неверная модель. Допустимые: {', '.join(valid_models)}"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove potentially dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and null bytes
    filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    max_length = 200
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]
    
    return filename or "file"


def validate_file_extension(
    filename: str,
    allowed_extensions: set
) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension.
    
    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (lowercase, without dot)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if '.' not in filename:
        return False, "Файл должен иметь расширение"
    
    ext = filename.rsplit('.', 1)[-1].lower()
    
    if ext not in allowed_extensions:
        return False, f"Неподдерживаемый формат. Допустимые: {', '.join(sorted(allowed_extensions))}"
    
    return True, None


def validate_file_size(
    size_bytes: int,
    max_size_mb: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.
    
    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in megabytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_bytes = max_size_mb * 1024 * 1024
    
    if size_bytes > max_bytes:
        return False, f"Файл слишком большой. Максимальный размер: {max_size_mb} MB"
    
    return True, None
