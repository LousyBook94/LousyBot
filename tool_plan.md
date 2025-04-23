# Tenor GIF Tool Documentation

## Tool Interaction Workflow

### AI Instruction Additions
Add to CUSTOM_INSTRUCTIONS:
```text
When appropriate, you MUST respond with tool usage tags. The system will:
1. Execute the requested tool
2. Return the raw result
3. Automatically feed this back to you
4. You then provide the final response

Follow these rules for tool usage:
- Use <tool_use> tags ONLY when needed
- Always include <thinking> analysis first
- If tool fails, suggest alternatives
- Maintain conversation flow

Example Flow:
User: Find a funny cat gif
AI: <tool_use><name>gif</name><prompt>funny cat</prompt></tool_use>
System: 
<tool_result>
    <name>gif</name>
    <result>https://media.tenor.com/.../happy-cat.gif</result>
</tool_use>
AI: Here's a hilarious cat GIF! <result>
```

### Tool Tag Format
The AI will use the following XML format to request a GIF:
```xml
<tool_use>
    <name>gif</name>
    <prompt>{search query}</prompt>
    <index>{result position}</index>
</tool_use>
```

### Response Handling Rules
1. If tool_use tags are present:
   - Extract and execute the tool request
   - Insert raw result into new message
   - Send back to AI for final response crafting
2. If tool_error occurs:
   - AI should explain error and suggest alternatives
3. For direct commands:
   - Bypass tool system and use enhanced AI flow

### Multi-Step Example
```xml
<!-- Initial AI Response -->
User wants a dancing parrot GIF. Should I search directly or ask clarifying questions?
<tool_use>
    <name>gif</name>
    <prompt>colorful dancing parrot</prompt>
    <index>3</index>
</tool_use>

<!-- System Response -->
<tool_result>
    <name>gif</name>
    <result>https://media.tenor.com/.../parrot-dance.gif</result>
</tool_use>

<!-- Final AI Response by modifying the existing message :] -->
Here's the 3rd result for "colorful dancing parrot"!
https://media.tenor.com/.../parrot-dance.gif
This tropical bird really knows how to move! 🦜💃
```

## Parameters
| Name   | Type   | Required | Default | Description                     |
|--------|--------|----------|---------|---------------------------------|
| name   | string | Yes      | -       | The name of the tool, always `gif` |
| prompt | string | Yes      | -       | Search query for GIFs           |
| index  | number | No       | 1       | Position of desired result (1-10) |

## Examples

### Basic Usage
**XML Format:**
```xml
<tool_use>
    <name>gif</name>
    <prompt>happy cat</prompt>
</tool_use>
```

**Discord Embed Feedback:**
```python
embed = discord.Embed(
    title="🎬 Using Tool",
    description="Tool: `gif`\nSearching Tenor for: `happy cat`",
    color=0x00ff00 # Green color for success/start
)
await ctx.send(embed=embed)
```

### With Index
**XML Format:**
```xml
<tool_use>
    <name>gif</name>
    <prompt>dancing banana</prompt>
    <index>3</index>
</tool_use>
```

**Discord Embed Feedback:**
```python
embed = discord.Embed(
    title="🔍 Using Tool",
    description="Tool: `gif`\nFetching 3rd result for: `dancing banana`",
    color=0xffa500 # Orange color for specific actions
).set_footer(text="Result positions 1-10 available")
await ctx.send(embed=embed)
```


### Successful Response
The tool handler will return the GIF URL within `<gif_result>` tags:
```xml
<tool_result>
    <name>gif</name>
    <result>https://media.tenor.com/.../happy-cat.gif</result>
</tool_use>
```
The bot should then extract this URL and post it.

### Error Response
The tool handler will return an error message within `<tool_error>` tags:
```xml
<tool_error>
No GIF found at that position
</tool_error>

errors would be dynamic as the error from the actual api
```
The bot should extract the error message and inform the user, e.g., "🚫 Error using gif tool: No GIF found at that position".

## Error Handling
Common errors:
- `No GIF found at that position`: Index exceeds result count or no results for prompt.
- `API connection failed`: Tenor service unavailable or network issue.
- `Invalid safety filter`: Content policy violation.
- `Invalid index`: Index is not a valid number or outside the 1-10 range.


## Configuration Setup

### Environment Variables
Add to `.env` and `.env.example`:
```env
TENOR_API_KEY="YOUR_API_KEY"
```

### Basic Usage Example
```python
# Set the API parameters
apikey = os.getenv("TENOR_API_KEY")
lmt = 8
ckey = "my_test_app"  # Client key for tracking

# Execute search
search_term = "excited"
r = requests.get(
    f"https://tenor.googleapis.com/v2/search?q={search_term}&key={apikey}&client_key={ckey}&limit={lmt}"
)

if r.status_code == 200:
    top_8gifs = r.json()
else:
    top_8gifs = None
```

> **Note:** Remember to add `import os` and `import requests` at the top of your file
also env vars are loaded in `src/config.py`