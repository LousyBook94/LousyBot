import discord
from discord import app_commands
from .config import CACHE_DIR, ALLOWED_CHANNELS, ALLOWED_GUILD_IDS, ALLOWED_GUILD_NAMES, USE_GUILD_ID
from src.provider_config import get_default_openai_client_and_model
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
    async def joke(interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
        except Exception as e:
            await send_error(interaction, e, prefix="⚠️ Could not defer interaction")
            return

        # Build the prompt and call the AI
        prompt = "Tell me a joke"
        try:
            # Use provider/model helper
            client, model_id = get_default_openai_client_and_model()
            completion = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                stream=False,
            )
            joke_text = completion.choices[0].message.content.strip()
            if not joke_text:
                joke_text = "😅 I couldn't come up with a joke right now!"
        except Exception as e:
            error_msg = f"⚠️ Oops an error occurred!\nError Code: AI_FETCH_FAILED\nError Message: {str(e)}"
            print(error_msg)
            joke_text = error_msg

        await interaction.followup.send(joke_text)