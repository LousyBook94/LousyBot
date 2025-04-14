import time
import asyncio
import discord
from .config import TEMPERATURE, DISABLE_STREAM, MAX_HISTORY_LEN, CUSTOM_INSTRUCTIONS, DEBUG
from src.provider_config import get_default_openai_client_and_model
from .cache_utils import load_channel_history, save_channel_history
from .mention_utils import resolve_discord_mentions
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

async def ai_processing_worker(request_queue):
    """
    Asynchronous worker to process AI requests from the queue.
    This function runs continuously, processing messages as they are added to the queue.
    """
    print("⚙️ AI Processing Worker started.")
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
                    response_content = completion.choices[0].message.content or ""
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
                    print(f"🤖 Sent non-streamed response to {message.channel.name}")
                else:
                    # 🟢 Streaming enabled: show "Thinking..." and stream as before
                    placeholder_message = await message.channel.send("🤔 Thinking... ")
                    # Use provider/model helper
                    client, model_id = get_default_openai_client_and_model()
                    stream = await client.chat.completions.create(
                        model=model_id,
                        messages=messages_for_api,
                        temperature=TEMPERATURE,
                        stream=True
                    )
                    accumulated_content = ""
                    chunk_to_send = ""
                    all_chunks = []
                    MAX_CHUNK = 1800

                    async for chunk in stream:
                        delta_content = chunk.choices[0].delta.content
                        if delta_content:
                            accumulated_content += delta_content
                            chunk_to_send += delta_content
                            # If we've exceeded MAX_CHUNK, wait for a newline to split
                            while len(chunk_to_send) > MAX_CHUNK:
                                # Find the last newline before MAX_CHUNK
                                split_idx = chunk_to_send.rfind('\n', 0, MAX_CHUNK)
                                if split_idx == -1:
                                    split_idx = MAX_CHUNK
                                send_part = chunk_to_send[:split_idx]
                                # Process mentions before sending
                                processed = resolve_discord_mentions(send_part, message.guild)
                                if placeholder_message:
                                    await placeholder_message.edit(content=processed)
                                    placeholder_message = None
                                else:
                                    await message.channel.send(processed)
                                chunk_to_send = chunk_to_send[split_idx:]
                    # Send any leftover text
                    if chunk_to_send.strip():
                        processed = resolve_discord_mentions(chunk_to_send, message.guild)
                        if placeholder_message:
                            await placeholder_message.edit(content=processed)
                        else:
                            await message.channel.send(processed)

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
