import time
import asyncio
import discord
import sys
from typing import Optional, List, Dict, Union

async def request_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    stream: bool = False
) -> Union[str, None]:
    """Universal function to request completions from the LLM.
    
    Args:
        messages: List of message dicts in OpenAI format
        temperature: Creativity level (0-2)
        stream: Whether to stream the response
        
    Returns:
        The completion text or None if failed
    """
    try:
        client, model_id = get_llm_client()
        completion = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            stream=stream
        )
        if stream:
            return None  # Streaming handled separately
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Error in request_completion: {e}")
        return None
from .config import TEMPERATURE, DISABLE_STREAM, MAX_HISTORY_LEN, CUSTOM_INSTRUCTIONS, DEBUG, STREAM_CHAR, DYNAMIC
from src.provider_config import get_llm_client
from .cache_utils import load_channel_history, save_channel_history
from .mention_utils import replace_mentions, get_ping_help
def get_users(guild, bot_user_id=None):
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

async def handle_message(message):
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
            + get_ping_help(message.guild)
            + "\n\n"
            + get_users(message.guild, bot_user_id=message.guild.me.id)
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
        client, model_id = get_llm_client()
        completion = await client.chat.completions.create(
            model=model_id,
            messages=messages_for_api,
            temperature=TEMPERATURE,
            stream=False
        )
        response_content = completion.choices[0].message.content or ""
        
        # Process mentions before sending
        processed_content = replace_mentions(response_content, message.guild)
        
        # Save AI response to history
        channel_history.append({"role": "assistant", "content": response_content})
        if len(channel_history) > MAX_HISTORY_LEN:
            channel_history = channel_history[-MAX_HISTORY_LEN:]
        save_channel_history(channel_id, channel_history)
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return False

async def llm_worker(request_queue):
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
                from .mention_utils import get_ping_help
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
                        + get_ping_help(message.guild)
                        + "\n\n"
                        + get_users(message.guild, bot_user_id=message.guild.me.id)
                    )
                    # --- Add Dynamic Response Instruction Conditionally ---
                    if DYNAMIC:
                        dynamic_instruction = (
                            "\n\n--- Dynamic Response Control ---\n"
                            "If you determine that a response is not necessary or appropriate for the current message "
                            "(e.g., it's casual chat not directed at you, or doesn't require an answer), "
                            "your *entire* response should consist *only* of the special marker `///noresponse`. "
                            "Do NOT include any other text, formatting, or emojis if you use `///noresponse`. "
                            "If you *do* want to respond, provide your response normally without including the `///noresponse` marker at all."
                        )
                        system_prompt += dynamic_instruction

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
                    client, model_id = get_llm_client()
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

                    # --- Dynamic Response Check (Non-Streaming) ---
                    if DYNAMIC and response_content.strip().startswith("///noresponse"):
                        print(f"🔇 Dynamic response: Suppressing non-streamed response for {message.author.name}")
                        # Skip saving history and sending the message
                        # We don't need to call task_done here, it's handled in the finally block
                        continue # Go to the next message in the queue
                    elif DYNAMIC:
                        # Remove marker if present, just in case it wasn't exactly at the start after stripping
                        response_content = response_content.replace("///noresponse", "", 1).strip()
                        # Ensure response_content is not empty after stripping the marker
                        if not response_content:
                            response_content = "😅 I couldn't come up with a response for that." # Fallback if only marker was present

                    # Process mentions before sending
                    processed_content = replace_mentions(response_content, message.guild)
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

                    # Save the original (marker-removed) response content to history
                    channel_history.append({"role": "assistant", "content": response_content})
                    if len(channel_history) > MAX_HISTORY_LEN:
                        channel_history = channel_history[-MAX_HISTORY_LEN:]
                    save_channel_history(channel_id, channel_history)
                    if is_test:
                        print("🤖 [TEST] Processing complete")
                    else:
                        print(f"🤖 Sent non-streamed response to {message.channel.name}")
                else:
                    # 🟢 Streaming enabled: show "Thinking..." only if DYNAMIC is false
                    placeholder_message = None
                    if not DYNAMIC:
                        placeholder_message = await message.channel.send("🤔 Thinking...")

                    client, model_id = get_llm_client()
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
                    first_chunk_processed = False # Flag to track if the first chunk logic has run
                    suppress_response = False # Flag to indicate if ///noresponse was found

                    async for chunk in stream:
                        if not chunk.choices or not chunk.choices[0].delta:
                            continue

                        delta_content = chunk.choices[0].delta.content
                        if delta_content:
                            accumulated_content += delta_content

                            # --- Dynamic Response Check (Streaming - First Chunk Only) ---
                            if DYNAMIC and not first_chunk_processed:
                                temp_stripped_content = accumulated_content.strip()
                                if temp_stripped_content.startswith("///noresponse"):
                                    print(f"🔇 Dynamic response: Suppressing streamed response for {message.author.name}")
                                    suppress_response = True
                                    if placeholder_message: # Delete thinking message if it exists (shouldn't in DYNAMIC mode, but check anyway)
                                        try: await placeholder_message.delete()
                                        except discord.NotFound: pass
                                    break # Exit the stream processing loop immediately
                                else:
                                    # Remove potential marker from the start if present
                                    # Check accumulated_content directly, not temp_stripped_content
                                    if accumulated_content.strip().startswith("///noresponse"):
                                        accumulated_content = accumulated_content.replace("///noresponse", "", 1) # Remove only first instance
                                first_chunk_processed = True # Mark first chunk logic as done

                            # If response is suppressed, don't process further chunks
                            if suppress_response:
                                continue

                            # Update message content
                            current_time = time.time()
                            if (STREAM_CHAR == 0 or
                                len(accumulated_content) - len(processed or "") >= STREAM_CHAR or
                                current_time - last_update_time >= update_interval):

                                processed = replace_mentions(accumulated_content, message.guild).replace(":white_circle:", "")
                                try:
                                    if placeholder_message: # Edit existing "Thinking..." message (only if not DYNAMIC)
                                        await placeholder_message.edit(content=processed + ":white_circle:" if processed else "...")
                                    elif not placeholder_message and processed: # DYNAMIC=true, no marker, first time sending
                                        placeholder_message = await message.channel.send(processed)
                                    elif placeholder_message and processed: # DYNAMIC=true, subsequent edits to the message we sent
                                         await placeholder_message.edit(content=processed)

                                    last_update_time = current_time
                                except discord.HTTPException as e:
                                    print(f"⚠️ Failed to edit/send message chunk: {e}")
                                    # Attempt to send as new message if edit failed
                                    try:
                                        # Send only the new part if possible, otherwise the whole processed content
                                        new_chunk_content = processed[len(getattr(placeholder_message, 'content', '')):] if placeholder_message else processed
                                        if new_chunk_content:
                                            sent_msg = await message.channel.send(new_chunk_content)
                                            # Update placeholder to the new message for future edits ONLY if it makes sense
                                            # If edits keep failing, this could spam. Maybe better to just let it fail?
                                            # For now, let's not update placeholder on failure to avoid spam.
                                            # placeholder_message = sent_msg
                                        else:
                                             print("⚠️ Edit failed, but no new content to send.")

                                    except discord.HTTPException as send_e:
                                         print(f"❌ Also failed to send message chunk as new message: {send_e}")


                    # --- Final Actions After Stream ---
                    if suppress_response:
                        # Response was suppressed, do nothing further
                        print(f"✅ Stream suppressed for {message.author.name} due to ///noresponse marker.")
                        pass # Explicitly do nothing
                    elif accumulated_content.strip():
                        # Stream finished normally, ensure final content is sent/edited
                        processed = replace_mentions(accumulated_content, message.guild)
                        try:
                            if placeholder_message: # Edit the message (either Thinking or the first sent chunk)
                                await placeholder_message.edit(content=processed)
                            elif processed: # Should have been created above if DYNAMIC=true and content exists
                                 # This case might happen if the entire response came in one go after the first check
                                 placeholder_message = await message.channel.send(processed) # Send final message
                        except discord.HTTPException as e:
                             print(f"⚠️ Failed to edit final message: {e}")
                             try:
                                 # Attempt final send again if edit failed
                                 if not placeholder_message or placeholder_message.content != processed:
                                     await message.channel.send(processed)
                             except discord.HTTPException as final_send_e:
                                 print(f"❌ Failed to send final message: {final_send_e}")


                        # Save to history (only if not suppressed)
                        channel_history.append({"role": "assistant", "content": accumulated_content})
                        if len(channel_history) > MAX_HISTORY_LEN:
                            channel_history = channel_history[-MAX_HISTORY_LEN:]
                        save_channel_history(channel_id, channel_history)
                        print(f"🤖 Sent streamed response to {message.channel.name}")
                    else: # Stream finished, but no content (and not suppressed)
                         error_msg = "😅 I couldn't come up with a response for that."
                         try:
                             if placeholder_message:
                                 await placeholder_message.edit(content=error_msg)
                             else: # DYNAMIC=true, no marker, but no content either
                                 await message.channel.send(error_msg)
                         except discord.HTTPException as e:
                              print(f"⚠️ Failed to send/edit empty response message: {e}")
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
