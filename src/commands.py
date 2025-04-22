import discord
from discord import app_commands
from .config import CACHE_DIR, ALLOWED_CHANNELS, ALLOWED_GUILD_IDS, ALLOWED_GUILD_NAMES, USE_GUILD_ID
from src.llm_client import request_completion
from .cache_utils import load_channel_history, save_channel_history
from .utils import get_error, send_error

def register_commands(tree, bot):
    @tree.command(name="clearcontext", description="Clear all context, cache, and bot memory for privacy or a fresh start.")
    async def clearcontext(interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
        except discord.errors.NotFound as e:
            if e.code == 10062:  # Unknown interaction
                print("⚠️ Interaction timed out or was already responded to")
                return
            await send_error(interaction, e,
                prefix="⚠️ Could not defer interaction",
                code="INTERACTION_FAILED")
            return
        except Exception as e:
            await send_error(interaction, e,
                prefix="⚠️ Could not defer interaction",
                code="INTERACTION_FAILED")
            return

        cleared_files = 0
        for f in CACHE_DIR.glob("*.lb01"):
            try:
                f.unlink()
                cleared_files += 1
            except Exception as e:
                print(get_error(e, prefix=f"⚠️ Failed to delete cache file {f}"))

        try:
            await interaction.followup.send(
                f"🧹 All history and cache cleared ({cleared_files} files removed)!"
            )
        except Exception as e:
            await send_error(interaction, e, prefix="⚠️ Failed to send clear confirmation")

    @tree.command(name="joke", description="Tells you a joke!")
    @app_commands.describe(about="What the joke should be about (optional)")
    async def joke(interaction: discord.Interaction, about: str = None):
        response_sent = False
        joke_text = "😅 I couldn't come up with a joke right now!"  # Default fallback

        try:
            # Defer immediately
            await interaction.response.defer(thinking=True, ephemeral=False)

            if interaction.is_expired():
                print("⚠️ Joke interaction expired before processing")
                return

            # Build prompt
            prompt = f"Tell me a joke about {about}" if about else "Tell me a joke"

            # Get joke from AI
            ai_response = await request_completion(
                messages=[
                    {"role": "system", "content": "You are a funny AI assistant. Tell a short, clean joke."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )

            # Update joke_text if AI provided a response
            if ai_response:
                joke_text = ai_response

        except Exception as e:
            error_msg = f"⚠️ Error generating joke: {str(e)}"
            print(error_msg)
            # Keep the default joke_text on error, or optionally set joke_text = error_msg
            # joke_text = error_msg # Uncomment this line to send the error message instead of the default joke

        finally:
            # Send the final response (either AI joke or fallback/error) ONCE
            if not response_sent and not interaction.is_expired():
                try:
                    await interaction.followup.send(joke_text)
                    response_sent = True # Mark as sent

                    # Save the ACTUAL sent message to history
                    try:
                        history = load_channel_history(str(interaction.channel_id))
                        history.append({
                            "role": "assistant",
                            "content": joke_text, # Save the final text that was sent
                            "type": "joke"
                        })
                        save_channel_history(str(interaction.channel_id), history)
                    except Exception as hist_e:
                        print(f"⚠️ Failed to save joke to history: {hist_e}")

                except Exception as send_e:
                    print(f"⚠️ Failed to send final joke/fallback message: {send_e}")
            elif interaction.is_expired():
                 print("⚠️ Interaction expired before final joke message could be sent.")