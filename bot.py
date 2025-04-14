import discord
import asyncio
from discord import app_commands
from asyncio import Queue
import aiohttp
import socket

from src.config import (
    DISCORD_TOKEN, ALLOWED_CHANNELS, USE_GUILD_ID, ALLOWED_GUILD_IDS, ALLOWED_GUILD_NAMES,
    CUSTOM_INSTRUCTIONS, MAX_HISTORY_LEN, WELCOME_MSG
)
from src.cache_utils import load_channel_history, save_channel_history
from src.mention_utils import resolve_mentions, replace_mentions_with_username_discriminator
from src.ai_processing import ai_processing_worker
from src.commands import register_commands
from src.provider_config import get_default_openai_client_and_model

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
request_queue = Queue()

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    print(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f"👂 Listening in channels: {ALLOWED_CHANNELS if ALLOWED_CHANNELS else 'None specified'}")
    print(f"📋 Connected guilds ({len(bot.guilds)}):")
    for g in bot.guilds:
        print(f"  - {g.name} (ID: {g.id})")
    if USE_GUILD_ID:
        print(f"👂 Allowed guilds (ID): {ALLOWED_GUILD_IDS if ALLOWED_GUILD_IDS else 'None specified'}")
    else:
        print(f"👂 Allowed guilds (Name): {ALLOWED_GUILD_NAMES if ALLOWED_GUILD_NAMES else 'None specified'}")
    print('------')

    # Sync commands
    if USE_GUILD_ID and ALLOWED_GUILD_IDS:
        for gid in ALLOWED_GUILD_IDS:
            print(f"🔄 Syncing slash commands to guild {gid}...")
            result = await tree.sync(guild=discord.Object(id=gid))
            print(f"    Synced commands: {', '.join(cmd.name for cmd in result)}")
        print(f"🌐 Slash commands synced to {len(ALLOWED_GUILD_IDS)} guild(s)!")
    else:
        print("🔄 Syncing global slash commands (can take up to 1 hour to appear)...")
        result = await tree.sync()
        print(f"    Synced commands: {', '.join(cmd.name for cmd in result)}")
        print("🌐 Slash commands synced globally!")
    # Register commands from src/commands.py
    register_commands(tree, bot)

    # (Ping help text is now dynamically injected per-message in ai_processing.py)

    # Start AI worker task
    asyncio.create_task(ai_processing_worker(request_queue))

    # Generate and send "back online" message (if enabled)
    if WELCOME_MSG:
        ai_announce_prompt = (
            "You are an AI assistant. "
            "Generate a friendly, energetic message to announce you are back online and ready to chat. "
            "Be creative and welcoming!"
        )
        ai_content = "🤖 Beep boop! I'm online and ready for action!" # Fallback
        try:
            try:
                client, model_id = get_default_openai_client_and_model()
                stream = await client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": ai_announce_prompt},
                        {"role": "user", "content": "Announce that the AI is back online."}
                    ],
                    temperature=0.8,
                    stream=True
                )
                final = ""
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        final += delta
                if final.strip():
                    ai_content = final.strip()
            except Exception as e:
                print("⚠️ Error generating AI online message: {e}")
                print("⚠️ AI client not available, using fallback online message.")
        except Exception as e:
            print(f"⚠️ Error generating AI online message: {e}")

        # Try to send the message to the first allowed channel
        try:
            first_guild = None
            first_channel = None
            if USE_GUILD_ID and ALLOWED_GUILD_IDS:
                for g in bot.guilds:
                    if g.id in ALLOWED_GUILD_IDS:
                        first_guild = g
                        break
            elif ALLOWED_GUILD_NAMES:
                for g in bot.guilds:
                    if g.name in ALLOWED_GUILD_NAMES:
                        first_guild = g
                        break

            if first_guild:
                for ch in first_guild.text_channels:
                    if ch.id in ALLOWED_CHANNELS:
                        first_channel = ch
                        break
                # Fallback: pick the first available text channel in the guild if no specific allowed channel found
                if not first_channel and first_guild.text_channels:
                    first_channel = first_guild.text_channels[0]
                    print(f"⚠️ No specific allowed channel found in guild {first_guild.name}, using first available: {first_channel.name}")

            if first_channel:
                await first_channel.send(ai_content)
                print(f"✅ Sent 'back online' message to {first_channel.name} in {first_guild.name}")
            else:
                print("⚠️ Could not find a suitable channel to send the 'back online' message.")
        except Exception as e:
            print(f"⚠️ Could not send back-online message: {e}")
    else:
        print("👋 Welcome message suppressed (WELCOME_MSG is false in .env)")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or message.webhook_id:
        return

    should_respond = False
    if message.channel.id in ALLOWED_CHANNELS:
        should_respond = True
    elif message.guild:
        if USE_GUILD_ID:
            if message.guild.id in ALLOWED_GUILD_IDS:
                should_respond = True
        else:
            if message.guild.name in ALLOWED_GUILD_NAMES:
                should_respond = True

    if not should_respond:
        return

    # Convert mentions to username#discriminator for AI input if enabled
    processed_content = (
        replace_mentions_with_username_discriminator(message.content, message.guild)
        if message.guild else message.content # Always include discriminator, even if 0000
    )
    # Overwrite the message.content for AI processing
    message.content = processed_content

    print(f"📥 Queuing request from {message.author.name} in {message.channel.name}: '{message.content[:50]}...'")
    await request_queue.put(message)

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Error: Failed to log in. Please check your DISCORD_TOKEN.")
    except aiohttp.client_exceptions.ClientConnectorDNSError as e:
        print("🌐❌ Internet connection error (can't reach Discord):", e)
        print("🔄 Retrying when connection is available...")
    except socket.gaierror as e:
        print("🌐❌ Network/DNS error (no internet?):", e)
        print("🔄 Retrying when connection is available...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
