# 📁 Project Structure — LousyBot 🤖

Welcome, LousyBook01! Here’s an overview of the project’s structure and what each part does:

---

## Root Directory

| Name              | Description                                                        |
|-------------------|--------------------------------------------------------------------|
| `.env`            | 🔐 Private environment variables (not tracked by git).             |
| `.env.example`    | 📝 Example environment variables file for setup reference.          |
| `.excalidraw`     | 🎨 Excalidraw diagram files, possibly for docs or planning.         |
| `.gitignore`      | 🚫 Lists files/folders to be ignored by git.                        |
| `bot.py`          | 🏁 Main entry point for the bot—launches the Discord bot.           |
| `bot.txt`         | 📄 Text file for notes, config, or data (usage may vary).           |
| `lousybot.png`    | 🖼️ Logo or image asset for the bot.                                |
| `requirements.txt`| 📦 Python dependencies required to run the bot.                     |
| `structure.md`    | 📚 This file! Describes the project structure.                      |

---

## `cache/` Directory

- Stores cached data for the bot.
  - Example: `1360593585409626142.lb01` (cache file for user/session/data).

---

## `src/` Directory — Main Source Code 🐍

| File / Folder              | Description                                             |
|----------------------------|---------------------------------------------------------|
| `__init__.py`              | 📦 Marks `src` as a Python package.                     |
| `ai_processing.py`         | 🤖 Handles AI algorithms, logic, or integrations.        |
| `cache_utils.py`           | 💾 Utilities for caching and retrieving data.            |
| `commands.py`              | 📝 Implements bot commands and command logic.            |
| `config.py`                | ⚙️ Loads and manages configuration settings.             |
| `mention_utils.py`         | 🚩 Handles user/bot mention parsing and utilities.       |
| `__pycache__/`             | 🏃 Python’s compiled bytecode cache (auto-generated).    |

---

## Notes

- All main Python code lives in `src/`.
- Cache files are stored in `cache/` to separate data from code.
- Environment variables are managed securely via `.env`.
- Edit `requirements.txt` to add/remove Python packages.

---

✨ Happy hacking! If you add new features, update this file to keep things clear for everyone. 😄🚀