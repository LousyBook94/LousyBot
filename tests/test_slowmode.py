from unittest.mock import AsyncMock, MagicMock, patch
import discord
from bot import bot
import pytest

@pytest.mark.asyncio
async def test_slowmode_detection():
    # Create mock message with slowmode channel
    message = AsyncMock(spec=discord.Message)
    message.channel.slowmode_delay = 5  # 5 second slowmode
    message.channel.send = AsyncMock()
    message.author.bot = False
    message.webhook_id = None
    message.guild = MagicMock()
    message.content = "test message"  # Not a command
    message.author.id = 12345  # Not an admin
    
    # Set ALLOWED_CHANNELS and disable admin checks
    with patch('bot.ALLOWED_CHANNELS', [message.channel.id]), \
         patch('bot.ADMIN_IDS', []):
        # Call on_message handler
        await bot.on_message(message)
        
        # Verify slowmode response
        message.channel.send.assert_awaited_once_with(
            "⏳ Please wait 5 seconds between messages (slowmode active)")

@pytest.mark.asyncio
async def test_normal_message_processing():
    # Create mock message without slowmode
    message = AsyncMock(spec=discord.Message)
    message.channel.slowmode_delay = 0
    message.guild = None
    message.content = "test message"
    message.author = MagicMock()
    message.author.bot = False
    message.webhook_id = None
    message.author.name = "TestUser"
    message.channel.name = "test-channel"
    
    # Mock queue and setup
    with patch('bot.request_queue.put', new_callable=AsyncMock) as mock_put:
        # Set ALLOWED_CHANNELS to include this channel
        with patch('bot.ALLOWED_CHANNELS', [message.channel.id]):
            await bot.on_message(message)
            mock_put.assert_awaited_once_with(message)

@pytest.mark.asyncio
async def test_slowmode_bypass_for_bot():
    # Create mock message from bot itself
    message = AsyncMock(spec=discord.Message)
    message.author = bot.user
    message.channel.slowmode_delay = 5
    
    # Call on_message handler
    await bot.on_message(message)
    
    # Verify no action taken
    message.channel.send.assert_not_called()