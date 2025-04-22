from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.commands import register_commands
import pytest

@pytest.mark.asyncio
async def test_clearcontext_command():
    # Setup mocks
    tree = MagicMock()
    bot = MagicMock()
    
    # Track registered commands
    registered_commands = []
    
    # Properly mock command decorator
    def mock_command(*args, **kwargs):
        def decorator(func):
            registered_commands.append({
                'name': kwargs.get('name'),
                'func': func
            })
            return func
        return decorator
        
    tree.command.side_effect = mock_command
    
    # Call registration
    register_commands(tree, bot)
    
    # Verify clearcontext command was registered
    clearcontext_cmd = next(
        (cmd for cmd in registered_commands
         if cmd['name'] == 'clearcontext'),
        None
    )
    assert clearcontext_cmd is not None
    
    # Test command execution
    interaction = AsyncMock()
    await clearcontext_cmd['func'](interaction)
    
    # Verify interaction handling
    interaction.response.defer.assert_awaited_once_with(thinking=True, ephemeral=False)
    interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_joke_command():
    # Setup mocks
    tree = MagicMock()
    bot = MagicMock()
    
    # Track registered commands
    registered_commands = []
    
    # Properly mock command decorator
    def mock_command(*args, **kwargs):
        def decorator(func):
            registered_commands.append({
                'name': kwargs.get('name'),
                'func': func
            })
            return func
        return decorator
        
    tree.command.side_effect = mock_command
    
    # Call registration
    register_commands(tree, bot)
    
    # Verify joke command was registered
    joke_cmd = next(
        (cmd for cmd in registered_commands
         if cmd['name'] == 'joke'),
        None
    )
    assert joke_cmd is not None
    
    # Test with successful joke response
    with patch('src.commands.request_completion', return_value="Why did the chicken cross the road?") as mock_request:
        
        interaction = AsyncMock()
        await joke_cmd['func'](interaction)
        
        interaction.followup.send.assert_awaited_once_with("Why did the chicken cross the road?")