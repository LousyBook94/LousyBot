import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.commands import register_commands

class TestCommands(unittest.IsolatedAsyncioTestCase):
    async def test_clearcontext_command(self):
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
        self.assertIsNotNone(clearcontext_cmd)
        
        # Test command execution
        interaction = AsyncMock()
        await clearcontext_cmd['func'](interaction)
        
        # Verify interaction handling
        interaction.response.defer.assert_awaited_once_with(thinking=True, ephemeral=False)
        interaction.followup.send.assert_awaited_once()

    async def test_joke_command(self):
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
        self.assertIsNotNone(joke_cmd)
        
        # Test with successful joke response
        with patch('src.commands.get_default_openai_client_and_model') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Why did the chicken cross the road?"))]
            )
            mock_get_client.return_value = (mock_client, "gpt-4")
            
            interaction = AsyncMock()
            await joke_cmd['func'](interaction)
            
            interaction.followup.send.assert_awaited_once_with("Why did the chicken cross the road?")

if __name__ == "__main__":
    unittest.main()