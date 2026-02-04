"""
Tests for bot utilities.
"""
import pytest

from bot.utils.helpers import (
    format_number,
    truncate_text,
    escape_html,
    format_duration,
    format_file_size,
    format_cost
)
from bot.utils.validators import (
    validate_prompt,
    validate_video_prompt,
    validate_image_size,
    validate_image_style,
    validate_video_duration,
    validate_video_model,
    sanitize_filename,
    validate_file_extension,
    validate_file_size
)


class TestHelpers:
    """Tests for helper functions."""
    
    def test_format_number_integer(self):
        """Test formatting integers."""
        assert format_number(1000) == "1,000"
        assert format_number(1000000) == "1,000,000"
        assert format_number(42) == "42"
    
    def test_format_number_float(self):
        """Test formatting floats."""
        assert format_number(1234.56) == "1,234.56"
        assert format_number(1234.5, precision=1) == "1,234.5"
        assert format_number(1234.5678, precision=3) == "1,234.568"
    
    def test_truncate_text_short(self):
        """Test truncating short text (no truncation needed)."""
        text = "Short text"
        assert truncate_text(text, max_length=100) == text
    
    def test_truncate_text_long(self):
        """Test truncating long text."""
        text = "This is a very long text that needs truncation"
        result = truncate_text(text, max_length=20)
        assert len(result) <= 20
        assert result.endswith("...")
    
    def test_truncate_text_custom_suffix(self):
        """Test truncating with custom suffix."""
        text = "This is a long text"
        result = truncate_text(text, max_length=15, suffix="…")
        assert result.endswith("…")
    
    def test_escape_html(self):
        """Test HTML escaping."""
        assert escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert escape_html("Hello & goodbye") == "Hello &amp; goodbye"
        assert escape_html("5 > 3 < 10") == "5 &gt; 3 &lt; 10"
    
    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        assert format_duration(30) == "30s"
        assert format_duration(1) == "1s"
    
    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        assert format_duration(60) == "1m"
        assert format_duration(90) == "1m 30s"
        assert format_duration(150) == "2m 30s"
    
    def test_format_duration_hours(self):
        """Test formatting duration in hours."""
        assert format_duration(3600) == "1h"
        assert format_duration(5400) == "1h 30m"
        assert format_duration(7200) == "2h"
    
    def test_format_file_size_bytes(self):
        """Test formatting file size in bytes."""
        assert format_file_size(500) == "500 B"
        assert format_file_size(1023) == "1023 B"
    
    def test_format_file_size_kb(self):
        """Test formatting file size in KB."""
        assert "KB" in format_file_size(1024)
        assert "KB" in format_file_size(500 * 1024)
    
    def test_format_file_size_mb(self):
        """Test formatting file size in MB."""
        assert "MB" in format_file_size(1024 * 1024)
        assert "MB" in format_file_size(10 * 1024 * 1024)
    
    def test_format_file_size_gb(self):
        """Test formatting file size in GB."""
        assert "GB" in format_file_size(1024 * 1024 * 1024)
    
    def test_format_cost_small(self):
        """Test formatting small costs."""
        assert format_cost(0.0001) == "$0.000100"
        assert format_cost(0.005) == "$0.0050"
    
    def test_format_cost_medium(self):
        """Test formatting medium costs."""
        assert format_cost(0.05) == "$0.0500"
        assert format_cost(0.5) == "$0.5000"
    
    def test_format_cost_large(self):
        """Test formatting large costs."""
        assert format_cost(1.23) == "$1.23"
        assert format_cost(10.50) == "$10.50"


class TestValidators:
    """Tests for validator functions."""
    
    def test_validate_prompt_valid(self):
        """Test valid prompts."""
        is_valid, error = validate_prompt("Hello world")
        assert is_valid is True
        assert error is None
    
    def test_validate_prompt_empty(self):
        """Test empty prompts."""
        is_valid, error = validate_prompt("")
        assert is_valid is False
        assert error is not None
        
        is_valid, error = validate_prompt("   ")
        assert is_valid is False
    
    def test_validate_prompt_too_short(self):
        """Test too short prompts."""
        is_valid, error = validate_prompt("Hi", min_length=5)
        assert is_valid is False
        assert "короткий" in error.lower() or "short" in error.lower()
    
    def test_validate_prompt_too_long(self):
        """Test too long prompts."""
        long_prompt = "a" * 5000
        is_valid, error = validate_prompt(long_prompt, max_length=4000)
        assert is_valid is False
        assert "длинный" in error.lower() or "long" in error.lower()
    
    def test_validate_video_prompt_valid(self):
        """Test valid video prompts."""
        is_valid, error = validate_video_prompt("A cat playing in the garden")
        assert is_valid is True
        assert error is None
    
    def test_validate_video_prompt_prohibited(self):
        """Test video prompts with prohibited content."""
        is_valid, error = validate_video_prompt("nude content")
        assert is_valid is False
        assert "запрещённый" in error.lower() or "prohibited" in error.lower()
    
    def test_validate_image_size_valid(self):
        """Test valid image sizes."""
        is_valid, _ = validate_image_size("1024x1024")
        assert is_valid is True
        
        is_valid, _ = validate_image_size("1792x1024")
        assert is_valid is True
        
        is_valid, _ = validate_image_size("1024x1792")
        assert is_valid is True
    
    def test_validate_image_size_invalid(self):
        """Test invalid image sizes."""
        is_valid, error = validate_image_size("512x512")
        assert is_valid is False
        assert error is not None
    
    def test_validate_image_style_valid(self):
        """Test valid image styles."""
        is_valid, _ = validate_image_style("vivid")
        assert is_valid is True
        
        is_valid, _ = validate_image_style("natural")
        assert is_valid is True
    
    def test_validate_image_style_invalid(self):
        """Test invalid image styles."""
        is_valid, error = validate_image_style("artistic")
        assert is_valid is False
        assert error is not None
    
    def test_validate_video_duration_valid(self):
        """Test valid video durations."""
        is_valid, _ = validate_video_duration(5)
        assert is_valid is True
        
        is_valid, _ = validate_video_duration(10)
        assert is_valid is True
    
    def test_validate_video_duration_invalid(self):
        """Test invalid video durations."""
        is_valid, error = validate_video_duration(15)
        assert is_valid is False
        assert error is not None
    
    def test_validate_video_model_valid(self):
        """Test valid video models."""
        is_valid, _ = validate_video_model("sora-2")
        assert is_valid is True
        
        is_valid, _ = validate_video_model("sora-2-pro")
        assert is_valid is True
    
    def test_validate_video_model_invalid(self):
        """Test invalid video models."""
        is_valid, error = validate_video_model("sora-3")
        assert is_valid is False
        assert error is not None
    
    def test_sanitize_filename_normal(self):
        """Test sanitizing normal filenames."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my file.txt") == "my file.txt"
    
    def test_sanitize_filename_dangerous(self):
        """Test sanitizing dangerous filenames."""
        assert "/" not in sanitize_filename("../../../etc/passwd")
        assert "\\" not in sanitize_filename("..\\..\\windows\\system32")
        assert "\x00" not in sanitize_filename("file\x00.txt")
    
    def test_sanitize_filename_long(self):
        """Test sanitizing long filenames."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 200
        assert result.endswith(".txt")
    
    def test_validate_file_extension_valid(self):
        """Test validating file extensions."""
        allowed = {"pdf", "doc", "docx"}
        
        is_valid, _ = validate_file_extension("document.pdf", allowed)
        assert is_valid is True
        
        is_valid, _ = validate_file_extension("file.DOCX", allowed)
        assert is_valid is True
    
    def test_validate_file_extension_invalid(self):
        """Test validating invalid file extensions."""
        allowed = {"pdf", "doc", "docx"}
        
        is_valid, error = validate_file_extension("file.exe", allowed)
        assert is_valid is False
        assert error is not None
    
    def test_validate_file_extension_no_extension(self):
        """Test validating files without extension."""
        allowed = {"pdf"}
        
        is_valid, error = validate_file_extension("filename", allowed)
        assert is_valid is False
    
    def test_validate_file_size_valid(self):
        """Test validating file size within limit."""
        is_valid, _ = validate_file_size(5 * 1024 * 1024, max_size_mb=20)
        assert is_valid is True
    
    def test_validate_file_size_invalid(self):
        """Test validating file size exceeding limit."""
        is_valid, error = validate_file_size(25 * 1024 * 1024, max_size_mb=20)
        assert is_valid is False
        assert "20 MB" in error
