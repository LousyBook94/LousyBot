import json
from pathlib import Path
from .config import CACHE_DIR

def load_channel_history(channel_id):
    """
    Load chat history for a specific channel from a file.

    Args:
        channel_id (str): The ID of the channel to load history for.

    Returns:
        list: The chat history as a list of messages, or an empty list if no history is found.
    """
    file_path = CACHE_DIR / f"{channel_id}.lb01"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load chat history for channel {channel_id}: {e}")
    return []

def save_channel_history(channel_id, history):
    """
    Save chat history for a specific channel to a file.

    Args:
        channel_id (str): The ID of the channel to save history for.
        history (list): The chat history to save.
    """
    file_path = CACHE_DIR / f"{channel_id}.lb01"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f)
    except Exception as e:
        print(f"⚠️ Failed to save chat history for channel {channel_id}: {e}")