# LousyBot Focused Improvement Plan 🛠️✨

This document outlines the high-impact improvements and feature upgrades for LousyBot, prioritized for maximum user experience, extensibility, and maintainability.

---

## 1. Testing 🧪

- **Create `tests/` folder** in the project root.
- Add unit tests for:
  - Command registration and permissions
  - Mention parsing/resolution
  - AI memory operations
  - Slowmode logic

---

## 2. New Slash Commands ➕

- **/help**: Lists all available commands and usage examples.
- **/quote**: Sends a random inspirational/funny quote (from API/local list).
- **/remindme**: Schedules a DM or channel reminder for the requesting user.
- **/summarize**: Summarizes a provided message, thread, or recent context.
- **/shutdownm**: Shuts down the bot (admin only).
- **/stats**: Shows bot/server stats (uptime, requests, users, etc).
- **/reload**: Reloads config/models/memory without full restart (admin only).

---

## 3. User Greeting 👋

- On `on_member_join`, send a personalized greeting in a welcome channel or DM.

---

## 4. Slowmode Fix ⏳

- Detect slowmode on channels before sending messages.
- If slowmode is active, queue/delay bot messages or provide user feedback.

---

## 5. Image Generation 🌅

- **User Command (`/imagine`)**:
  - `/imagine prompt: string` allows users to request image generation via pollinations.ai.
  - Show a "Please wait... Generating Image..." message while processing.
  - Post the generated image on success or an error message on failure.
- **AI Tool (`image_generation`)**:
  - The AI can request image generation internally using a tool call (e.g., `{"tool": "image_generation", "prompt": "..."}`).
  - The bot handles the generation and includes the image in its response.

---

## 6. AI Memory System 🧠

- Add a persistent memory store (e.g., JSON or lightweight DB).
- **AI Tool (`memory_tool`)**: Allow AI (via special tool-calls like `{"tool": "memory_tool", "action": "append", "data": {...}}`) to:
  - Append new facts/entries (`action: "append"`)
  - Delete or modify stored entries (`action: "delete" / "modify"`)
  - Create links/associations (`action: "link"`)
  - Search/retrieve memory (`action: "search"`)
- **User Commands**: Expose admin/user commands for memory inspection and management (e.g., `/memory list`, `/memory delete <id>`).

---

## 7. QOL Features ✅

- **Status cycling:** Rotate bot presence/activity messages.
- **Better error feedback:** Inform users of permission/config errors.
- **Command autocomplete:** Use Discord's autocomplete API for command params.

---

## 🗺️ Roadmap (Mermaid)

```mermaid
graph TD
    A[Tests] --> B[Unit tests for commands, memory, slowmode]
    C[Slash Commands] --> D[/help]
    C --> E[/quote]
    C --> F[/remindme]
    C --> G[/summarize]
    C --> H[/shutdownm]
    C --> I[/stats]
    C --> J[/reload]
    K[User Greeting] --> L[Welcome on join]
    M[Slowmode] --> N[Queue/delay messages]
    O[Image Generation] --> P[/imagine command & AI tool]
    O --> P1[Pollinations.ai integration]
    O --> P2[User feedback msg]
    Q[AI Memory] --> R[Persistent store & AI tool interface]
    Q --> S[User memory management commands]
    T[QOL] --> U[Status cycling]
    T --> V[Better error feedback]
    T --> W[Autocomplete]
```

---

*Let this plan guide the next development sprint for LousyBot! 😺🚀*