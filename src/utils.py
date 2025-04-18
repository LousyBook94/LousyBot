"""Utility functions for error handling and other common operations."""
from typing import Optional, Union
import discord

def get_error(
    error: Union[Exception, str],
    prefix: str = "⚠️ Oops an error occurred!",
    code: Optional[str] = None
) -> str:
    """Format an error message consistently.
    
    Args:
        error: The error/exception or error message string
        prefix: Custom prefix for the error message
        code: Optional error code to include
        
    Returns:
        Formatted error message string
    """
    error_msg = str(error)
    error_code = code if code else getattr(error, 'code', 'UNKNOWN')
    return f"{prefix}\nError Code: {error_code}\nError Message: {error_msg}"

async def send_error(
    destination: Union[discord.Interaction, discord.TextChannel],
    error: Union[Exception, str],
    **kwargs
) -> None:
    """Send an error message to a Discord destination with fallback handling.
    
    Args:
        destination: Discord interaction or channel to send to
        error: Error to format and send
        kwargs: Additional args for get_error()
    """
    error_msg = get_error(error, **kwargs)
    
    try:
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                await destination.followup.send(error_msg)
            else:
                await destination.response.send_message(error_msg)
        else:
            await destination.send(error_msg)
    except Exception as e:
        print(f"Failed to send error message: {e}")
        print(f"Original error: {error_msg}")

def log_error(
    error: Union[Exception, str],
    context: str = "",
    **kwargs
) -> None:
    """Log an error with context.
    
    Args:
        error: Error to log
        context: Additional context about where error occurred
        kwargs: Additional args for get_error()
    """
    error_msg = get_error(error, **kwargs)
    if context:
        error_msg = f"{context}\n{error_msg}"
    print(error_msg)