import unittest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.ai_processing import build_user_list

class TestAIProcessing(unittest.IsolatedAsyncioTestCase):
    async def test_build_user_list(self):
        # Create mock guild with test users
        guild = MagicMock(spec=discord.Guild)
        user1 = MagicMock()
        user1.name = "TestUser"
        user1.discriminator = "1234"
        user1.id = 123456789012345678
        
        user2 = MagicMock()
        user2.name = "AnotherUser"
        user2.discriminator = "5678"
        user2.id = 987654321098765432
        
        guild.members = [user1, user2]
        
        # Test without bot user
        result = build_user_list(guild)
        self.assertIn("TestUser#1234 | 123456789012345678", result)
        self.assertIn("AnotherUser#5678 | 987654321098765432", result)
        
        # Test with bot user
        result = build_user_list(guild, bot_user_id=123456789012345678)
        self.assertIn("TestUser#1234 | 123456789012345678 | (Your Account)", result)

    async def test_message_processing(self):
        """Test the core message processing logic directly"""
        from src.ai_processing import process_message
        
        # Setup test message with all required attributes
        message = AsyncMock(spec=discord.Message)
        message.channel.id = "12345"
        message.author.name = "TestUser"
        message.author.discriminator = "1234"
        message.author.id = 123456789012345678
        message.content = "test message"
        message.guild = MagicMock()
        message.guild.me = MagicMock()
        message.guild.me.id = 987654321098765432
        message.author.bot = False
        message.webhook_id = None
        message.guild.get_member.return_value = message.author

        # Mock dependencies with proper imports
        with patch('bot.ALLOWED_CHANNELS', [message.channel.id]), \
             patch('src.ai_processing.load_channel_history', return_value=[]) as mock_load, \
             patch('src.ai_processing.save_channel_history') as mock_save, \
             patch('src.provider_config.get_default_openai_client_and_model') as mock_get_client:
            
            # Setup mock AI response
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            )
            mock_get_client.return_value = (mock_client, "gpt-4")

            # Call process_message directly
            result = await process_message(message)
            
            # Verify results
            self.assertTrue(result)
            mock_load.assert_called_once_with(str(message.channel.id))
            self.assertEqual(mock_save.call_count, 2)  # Once for user msg, once for AI response
            
            # Verify history was loaded and saved
            mock_load.assert_called_once_with(str(message.channel.id))
            self.assertEqual(mock_save.call_count, 2)  # Once for user msg, once for AI response

if __name__ == "__main__":
    unittest.main()