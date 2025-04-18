import time
import asyncio
import discord
import sys
from .config import TEMPERATURE, DISABLE_STREAM, MAX_HISTORY_LEN, CUSTOM_INSTRUCTIONS, DEBUG, STREAM_CHAR
from src.provider_config import get_default_openai_client_and_model
from .cache_utils import load_channel_history, save_channel_history
from .mention_utils import resolve_discord_mentions, build_ping_help_text
def build_user_list(guild, bot_user_id=None):
    """
    Build a user list string for the guild.
    Format:
    Server User List:
    - username#discriminator | user_id | (You're Account)  # Only if this is the bot's own account
    """
    if not guild or not hasattr(guild, "members"):
        return "Server User List:\n(No user list available)"
    user_lines = []
    for m in guild.members:
        line = f"- {m.name}#{m.discriminator} | {m.id}"
        if bot_user_id is not None and m.id == bot_user_id:
            line += " | (Your Account)"
        user_lines.append(line)
    return "Server User List:\n" + "\n".join(sorted(set(user_lines)))

async def process_message(message):
    """
    Process a single message through the AI pipeline.
    Returns True if processed successfully, False otherwise.
    """
    print(f"DEBUG: Starting message processing for channel {message.channel.id}")
    channel_id = str(message.channel.id)
    
    try:
        print("DEBUG: Loading channel history")
        channel_history = load_channel_history(channel_id)
    except Exception as e:
        print(f"DEBUG: Failed to load history: {e}")
        return False
    
    # Compose user message context
    user_content = f"{message.author.name}#{message.author.discriminator} ({message.author.id}) says: {message.content}"

    # Update channel history
    channel_history.append({
        "role": "user",
        "name": str(message.author.name),
        "discriminator": str(message.author.discriminator),
        "user_id": str(message.author.id),
        "content": message.content
    })
    
    if len(channel_history) > MAX_HISTORY_LEN:
        channel_history = channel_history[-MAX_HISTORY_LEN:]
    save_channel_history(channel_id, channel_history)

    # Prepare messages for API
    messages_for_api = []
    if CUSTOM_INSTRUCTIONS:
        commands_list = (
            "Available Bot Commands:\n"
            "• /clearcontext — Clear all context, cache, and bot memory for privacy or a fresh start.\n"
            "• /joke — Tells you a joke!\n"
            "You can use these slash commands anytime for special actions.\n"
        )
        system_prompt = (
            CUSTOM_INSTRUCTIONS
            + "\n\n"
            + commands_list
            + "\n\n"
            + build_ping_help_text(message.guild)
            + "\n\n"
            + build_user_list(message.guild, bot_user_id=message.guild.me.id)
        )
        messages_for_api.append({"role": "system", "content": system_prompt})
    
    messages_for_api.extend([
        {
            "role": entry["role"],
            "content": (
                f'{entry.get("name", "")}#{entry.get("discriminator", "????")} ({entry.get("user_id", "unknown")}) says: {entry["content"]}'
                if entry["role"] == "user" else entry["content"]
            )
        }
        for entry in channel_history
    ])

    try:
        client, model_id = get_default_openai_client_and_model()
        completion = await client.chat.completions.create(
            model=model_id,
            messages=messages_for_api,
            temperature=TEMPERATURE,
            stream=False
        )
        response_content = completion.choices[0].message.content or ""
        
        # Process mentions before sending
        processed_content = resolve_discord_mentions(response_content, message.guild)
        
        # Save AI response to history
        channel_history.append({"role": "assistant", "content": response_content})
        if len(channel_history) > MAX_HISTORY_LEN:
            channel_history = channel_history[-MAX_HISTORY_LEN:]
        save_channel_history(channel_id, channel_history)
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return False

async def ai_processing_worker(request_queue):
    """
    Asynchronous worker to process AI requests from the queue.
    This function runs continuously, processing messages as they are added to the queue.
    """
    print("⚙️ AI Processing Worker started.")
    is_test = 'unittest' in sys.modules
    
    while True:
        try:
            message = await request_queue.get()
            print(f"⚙️ Processing request from {message.author.name}...")

            placeholder_message = None
            try:
                channel_id = str(message.channel.id)
                channel_history = load_channel_history(channel_id)
                # 🟢 Compose user message context
                user_content = f"{message.author.name}#{message.author.discriminator} ({message.author.id}) says: {message.content}"

                # Update channel history
                channel_history.append({
                    "role": "user",
                    "name": str(message.author.name),
                    "discriminator": str(message.author.discriminator),
                    "user_id": str(message.author.id),
                    "content": message.content
                })
                if len(channel_history) > MAX_HISTORY_LEN:
                    channel_history = channel_history[-MAX_HISTORY_LEN:]
                save_channel_history(channel_id, channel_history)

                # Prepare messages for API
                messages_for_api = []
                from .mention_utils import build_ping_help_text
                if CUSTOM_INSTRUCTIONS:
                    commands_list = (
                        "Available Bot Commands:\n"
                        "• /clearcontext — Clear all context, cache, and bot memory for privacy or a fresh start.\n"
                        "• /joke — Tells you a joke!\n"
                        "You can use these slash commands anytime for special actions.\n"
                    )
                    system_prompt = (
                        CUSTOM_INSTRUCTIONS
                        + "\n\n"
                        + commands_list
                        + "\n\n"
                        + build_ping_help_text(message.guild)
                        + "\n\n"
                        + build_user_list(message.guild, bot_user_id=message.guild.me.id)
                    )
                    messages_for_api.append({"role": "system", "content": system_prompt})
                messages_for_api.extend([
                    {
                        "role": entry["role"],
                        "content": (
                            f'{entry.get("name", "")}#{entry.get("discriminator", "????")} ({entry.get("user_id", "unknown")}) says: {entry["content"]}'
                            if entry["role"] == "user" else entry["content"]
                        )
                    }
                    for entry in channel_history
                ])

                if DISABLE_STREAM:
                    # 🚫 Streaming disabled: just get a single, final AI response and send it
                    # Use provider/model helper
                    client, model_id = get_default_openai_client_and_model()
                    completion = await client.chat.completions.create(
                        model=model_id,
                        messages=messages_for_api,
                        temperature=TEMPERATURE,
                        stream=False
                    )
                    if not completion.choices or not completion.choices[0].message:
                        response_content = "😅 I couldn't come up with a response for that."
                    else:
                        response_content = completion.choices[0].message.content or "😅 I couldn't come up with a response for that."
                    if DEBUG:
                        print(f"Response from AI : {response_content!r}")
                    # Process mentions before sending
                    processed_content = resolve_discord_mentions(response_content, message.guild)
                    if DEBUG:
                        print(f"Modified Response from AI : {processed_content!r}")
                    # Split into <2000 char chunks for Discord
                    to_send = processed_content if processed_content else "😅 I couldn't come up with a response for that."
                    while to_send:
                        chunk = to_send[:2000]
                        # Try to break at newline if over 1800 chars
                        if len(chunk) == 2000 and '\n' in chunk[1800:]:
                            split = chunk.rfind('\n', 1800)
                            if split != -1:
                                chunk = chunk[:split]
                        await message.channel.send(chunk)
                        to_send = to_send[len(chunk):]

                    channel_history.append({"role": "assistant", "content": response_content})
                    if len(channel_history) > MAX_HISTORY_LEN:
                        channel_history = channel_history[-MAX_HISTORY_LEN:]
                    save_channel_history(channel_id, channel_history)
                    if is_test:
                        print("🤖 [TEST] Processing complete")
                    else:
                        print(f"🤖 Sent non-streamed response to {message.channel.name}")
                else:
                    # 🟢 Streaming enabled: show "Thinking..." and stream incrementally
                    placeholder_message = await message.channel.send("🤔 Thinking...")
                    client, model_id = get_default_openai_client_and_model()
                    stream = await client.chat.completions.create(
                        model=model_id,
                        messages=messages_for_api,
                        temperature=TEMPERATURE,
                        stream=True
                    )
                    
                    accumulated_content = ""
                    processed = "" # Initialize processed
                    last_update_time = time.time()
                    update_interval = 0.5  # Update at least every 0.5 seconds
                    MAX_CHUNK = 1800

                    async for chunk in stream:
                        if not chunk.choices or not chunk.choices[0].delta:
                            continue
                            
                        delta_content = chunk.choices[0].delta.content
                        if delta_content:
                            accumulated_content += delta_content
                            
                            # Update more frequently - either when we have enough content or time has passed
                            current_time = time.time()
                            if (STREAM_CHAR == 0 or  # Update on every character if 0
                                len(accumulated_content) - len(processed or "") >= STREAM_CHAR or
                                current_time - last_update_time >= update_interval):
                                
                                processed = resolve_discord_mentions(accumulated_content, message.guild)
                                try:
                                    await placeholder_message.edit(content=processed)
                                    last_update_time = current_time
                                except discord.HTTPException:
                                    # If edit fails, send as new message and create new placeholder
                                    await message.channel.send(processed)
                                    placeholder_message = await message.channel.send("...")
                    
                    # Final update with complete content
                    if accumulated_content.strip():
                        processed = resolve_discord_mentions(accumulated_content, message.guild)
                        await placeholder_message.edit(content=processed)
                    else:
                        await placeholder_message.edit(content="😅 I couldn't come up with a response for that.")

                    # Save to history
                    if accumulated_content:
                        channel_history.append({"role": "assistant", "content": accumulated_content})
                        if len(channel_history) > MAX_HISTORY_LEN:
                            channel_history = channel_history[-MAX_HISTORY_LEN:]
                        save_channel_history(channel_id, channel_history)
                        print(f"🤖 Sent streamed response (chunked) to {message.channel.name}")
                    else:
                        if placeholder_message:
                            await placeholder_message.edit(content="😅 I couldn't come up with a response for that.")
                        print("⚠️ AI stream finished with no content.")

            except Exception as e:
                print(f"❌ Error during AI processing/streaming for {message.author.name}: {e}")
                error_message_content = "😵‍💫 Oops! Something went wrong while processing your request."
                try:
                    if placeholder_message:
                        await placeholder_message.edit(content=error_message_content)
                    else:
                        await message.channel.send(error_message_content)
                except discord.HTTPException as http_e:
                    print(f"❌ Failed to send error message to Discord: {http_e}")
            finally:
                request_queue.task_done()
                print(f"✅ Finished processing request from {message.author.name}.")
                print("====\n")

        except Exception as e:
            print(f"❌ Critical error in AI worker loop: {e}")
            await asyncio.sleep(5)
