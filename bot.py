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

# Load admin IDs
ADMIN_IDS = []
try:
    # Assuming admin.txt is in the same directory as bot.py
    with open('admin.txt') as f:
        ADMIN_IDS = [int(line.strip()) for line in f if line.strip()]
    print(f"✅ Loaded {len(ADMIN_IDS)} admin IDs")
    print("ℹ️ Type '!sync' with your userid in admin.txt to sync commands")
except FileNotFoundError:
    print("⚠️ admin.txt not found, no admin IDs loaded.")
    ADMIN_IDS = []
except Exception as e:
    print(f"❌ Failed to load admin IDs: {e}")
    ADMIN_IDS = []

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

    # Register commands from src/commands.py FIRST!
    register_commands(tree, bot)
    print("✅ Commands registered locally.")
    # Syncing is now handled by the !sync command below.
    # You might want to run !sync once after starting the bot.

    # Start AI worker task
    asyncio.create_task(ai_processing_worker(request_queue))

    # Generate and send "back online" message (if enabled)
    if WELCOME_MSG:
        ai_announce_prompt = (
            "You are an AI assistant. "
            "Generate a friendly, energetic message to announce you are back online and ready to chat. "
            "Be creative and welcoming!"
        )
        # Fun rotating fallback messages
        fallbacks = [
            "🤖 Beep boop! Systems nominal and ready for your commands!",
            "✨ Back in action! What can I help you with today?",
            "🚀 Online and operational! Let's chat!",
            "👋 Hello world! Ready to assist!",
            "💡 Lights on! Ask me anything!"
        ]
        import random
        ai_content = random.choice(fallbacks) # Fallback
        try:
            client, model_id = get_default_openai_client_and_model()
            try:
                response = await client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": ai_announce_prompt},
                        {"role": "user", "content": "Announce that the AI is back online."}
                    ],
                    temperature=0.8
                )
                if response.choices and len(response.choices) > 0:
                    ai_content = response.choices[0].message.content or ai_content
            except Exception as e:
                print(f"⚠️ Error generating AI online message: {str(e)}")
                print("⚠️ AI client not available, using fallback online message.")
                if hasattr(e, 'response'):
                    print(f"⚠️ API Response: {e.response.text if e.response else 'None'}")
        except Exception as e:
            print(f"⚠️ Error initializing AI client: {e}")

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

    # Handle !sync command
    if message.content.startswith('!sync'):
        if message.author.id not in ADMIN_IDS:
            await message.channel.send(":no_entry_sign: You don't have permission to sync commands!")
            return

        sync_target = message.content[len('!sync'):].strip()
        synced_commands = []
        try:
            await message.channel.send(":arrows_counterclockwise: Syncing commands...")
            if sync_target == "guild" and USE_GUILD_ID and ALLOWED_GUILD_IDS:
                for gid in ALLOWED_GUILD_IDS:
                    synced_commands = await tree.sync(guild=discord.Object(id=gid))
                await message.channel.send(f":white_check_mark: Synced {len(synced_commands)} commands to {len(ALLOWED_GUILD_IDS)} specified guild(s)!")
            elif sync_target == "clear_guild" and USE_GUILD_ID and ALLOWED_GUILD_IDS:
                 for gid in ALLOWED_GUILD_IDS:
                    tree.clear_commands(guild=discord.Object(id=gid))
                    await tree.sync(guild=discord.Object(id=gid))
                 await message.channel.send(f":wastebasket: Cleared commands from {len(ALLOWED_GUILD_IDS)} specified guild(s)!")
            elif sync_target == "copy_guild" and USE_GUILD_ID and ALLOWED_GUILD_IDS:
                for gid in ALLOWED_GUILD_IDS:
                    guild_obj = discord.Object(id=gid)
                    tree.copy_global_to(guild=guild_obj)
                    synced_commands = await tree.sync(guild=guild_obj)
                await message.channel.send(f":clipboard: Copied global commands and synced {len(synced_commands)} commands to {len(ALLOWED_GUILD_IDS)} specified guild(s)!")
            else: # Default to global sync
                synced_commands = await tree.sync()
                await message.channel.send(f":white_check_mark: Synced {len(synced_commands)} commands globally!")
            print(f"    Synced commands via !sync: {', '.join(cmd.name for cmd in synced_commands)}")
        except Exception as e:
            await message.channel.send(f":x: Sync failed: {e}")
            print(f"❌ Error during !sync: {e}")
        return # Don't process !sync as a regular message

    # --- Rest of on_message logic ---
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

    # Check channel slowmode
    slowmode_delay = getattr(message.channel, 'slowmode_delay', 0)
    if slowmode_delay > 0:
        print(f"⏳ Slowmode active ({slowmode_delay}s) in {message.channel.name}")
        await message.channel.send(
            f"⏳ Please wait {slowmode_delay} seconds between messages (slowmode active)"
        )
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
