# LousyBot 🤖

Welcome to **LousyBot** — a modular, customizable Discord bot created by [LousyBook01](https://github.com/LousyBook-94).  
LousyBot features multi-provider AI support, robust config management, and a friendly codebase for easy extension!

---

## 🚀 Features

- 🔒 Secure: Sensitive config files are never committed.
- 🤖 AI integration via flexible provider/model system (no hardcoded OpenAI keys!).
- 📝 Easily configurable via `.env` and plaintext config files.
- 😺 Fun, expressive, and emoji-rich interaction style.
- 🛠️ Extensible: Clean, modular code, ready for plugins and custom logic.

---

## 🛠️ Setup

1. **Clone the repo:**
   ```sh
   git clone https://github.com/<your-username>/LousyBot.git
   cd LousyBot
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   - Copy `.env.example` to `.env` and fill in your Discord bot token and other variables.
   - Edit `model/provider.txt` and `model/models.txt` (see `.example` files for format).

4. **Start the bot:**
   ```sh
   python bot.py
   ```

---

## 📁 Project Structure

```
.
├── .env.example
├── .gitignore
├── bot.py
├── bot.txt
├── cache/
├── lousybot.png
├── model/
│   ├── models.txt
│   ├── models.txt.example
│   └── provider.txt.example
├── README.md
├── requirements.txt
├── structure.md
└── src/
    ├── __init__.py
    ├── ai_processing.py
    ├── cache_utils.py
    ├── commands.py
    ├── config.py
    ├── mention_utils.py
    └── provider_config.py
```

See **structure.md** for detailed explanations of each file and directory.

---

## 🔐 Security

- **Never commit `.env` or `model/provider.txt`!** These files are in `.gitignore` by default.
- Only `.env.example` and `provider.txt.example` are shared for onboarding.

---

## 🤝 Contributing

Pull requests and suggestions are welcome!  
Please update `structure.md` if you add new modules or important files.

---

## 🙏 Credits

- Created by [LousyBook01](https://github.com/LousyBook-94)
- Powered by Python, discord.py, and modern AI APIs

---

**Happy hacking!** ✨