import re
import discord
import logging # Optional: for logging lookup failures
from functools import partial

import os

def parse_admin_file(file_path="admin.txt"):
    """
    Parses admin.txt, validates each line, and returns (valid_admins, error_lines, admin_list_str).
    - valid_admins: set of valid admin entries (user#discriminator or user_id)
    - error_lines: list of invalid lines
    - admin_list_str: formatted string for instructions
    """
    valid_admins = set()
    error_lines = []
    admin_lines = []
    if not os.path.exists(file_path):
        return valid_admins, ["admin.txt not found!"], "❗ admin.txt not found!"
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if (
                (line.isdigit() and 15 <= len(line) <= 21)
                or (("#" in line) and len(line.split("#")) == 2 and line.split("#")[1].isdigit())
            ):
                valid_admins.add(line)
                admin_lines.append(f"  • {line}")
            else:
                error_lines.append(f"Line {i}: '{line}'")
    admin_list_str = "📋 Current admin list for @everyone/@here pings:\n" + ("\n".join(admin_lines) if admin_lines else "  • (none)")
    if error_lines:
        admin_list_str += "\n❗ Invalid lines in admin.txt (ignored):\n" + "\n".join(f"  - {err}" for err in error_lines)
    return valid_admins, error_lines, admin_list_str

_, _, ADMIN_LIST_FOR_INSTRUCTIONS = parse_admin_file()

def build_ping_help_text(guild=None):
    """
    Returns the full instructions string for the model, including admin list and available roles.
    """
    roles_list = get_all_roles_string(guild)
    return (
        "🔔 A mention (also called a ping or tag) directly notifies a Discord user! 🏷️\n\n"
        "➡️ To mention a specific user in AI output, ALWAYS use the format: <@username#discriminator> (e.g. <@LousyBook01#1234>) or <@user_id> (e.g. <@1217486885421711405>) — this must match a real user from the server user list provided.\n"
        "🚫 NEVER output <@user>, <@userid>, or any placeholder/guess for a mention — these will NOT ping anyone and are considered invalid for AI output.\n"
        "❌ Do NOT use made-up names, placeholders like 'user', or generic text like 'user_id'. Always reference a real user from the provided list.\n"
        "✅ If you need to ping the sender of a message, their username, discriminator, and user ID are always included in the message context, so you can construct a valid ping for them!\n"
        "👥 To ping everyone, use <@everyone>. To ping a role, use <@roleName> (e.g. <@owner> or <@here>). Only user pings require the #discriminator — everyone/role pings do NOT.\n"
        "⚠️ Only users listed in 'admin.txt' (one per line, as user#1234 or user_id) are allowed to ask the bot to perform @everyone or @here pings. If you are not in this list, your request for @everyone/@here will be ignored, but you can still ping individuals and roles! 😎\n"
        f"{ADMIN_LIST_FOR_INSTRUCTIONS}\n"
        "📋 Available roles you can mention:\n"
        f"{roles_list}\n"
        "⭐ TL;DR: <@username#discriminator> or <@user_id> for user pings, <@everyone>/<@roleName> for groups/roles, all must be in angle brackets and start with @! Only admin-listed users can trigger @everyone/@here."
    )

def _mention_replacer(match: re.Match, guild: discord.Guild | None) -> str:
    """
    Internal helper function called by re.sub for each potential mention match.
    Analyzes the content within <@...> and performs lookups/replacements.

    Supports:
    - <@user_id> (e.g. <@1217486885421711405>)
    - <@username#discriminator> (e.g. <@LousyBook01#1234>)
    - <@everyone>
    - <@roleName>

    Leaves unrecognized or unresolvable patterns unchanged.
    """
    original_mention = match.group(0) # The full matched string, e.g., "<@TestUser#1234>"
    content = match.group(2)          # The part inside the brackets, e.g., "TestUser#1234"

    # 1. Handle <@everyone> and <@here> - output as @everyone/@here (no brackets)
    if content == "everyone" or content == "here":
        return f"@{content}"

    # --- Guild is required for user/role lookups beyond this point ---
    if guild is None:
        # Cannot perform lookups. Only allow <@user_id> format if it looks like one,
        # otherwise return original to avoid breaking things.
        if content.isdigit() and 15 <= len(content) <= 21: # Basic check for ID format
             return original_mention # Return "<@user_id>"
        else:
             return original_mention # Cannot resolve name#disc or roles

    # 2. Handle <@user_id>
    if content.isdigit():
        try:
            user_id = int(content)
            if 15 <= len(content) <= 21:
                 return f"<@{user_id}>"
        except ValueError:
            pass # Fall through

    # 3. Handle <@username#discriminator>
    if '#' in content:
        parts = content.rsplit('#', 1)
        if len(parts) == 2:
            name_part, disc_part = parts
            if disc_part.isdigit() and 1 <= len(disc_part) <= 4:
                member = discord.utils.get(guild.members, name=name_part, discriminator=disc_part)
                if member:
                    return f"<@{member.id}>"
                else:
                    return original_mention

    # 4. Handle <@roleName> - output as @roleName (no brackets) if role exists
    role = discord.utils.get(guild.roles, name=content)
    if role:
        return f"@{content}"

    # 5. Fallback: Not a recognized/resolvable pattern
    return original_mention

def resolve_discord_mentions(text: str, guild: discord.Guild | None) -> str:
    """
    Scans input text for specific mention formats (<@user_id>,
    <@username#discriminator>, <@everyone>, <@roleName>) and resolves
    them to the appropriate Discord mention strings.

    - <@user_id> -> <@user_id>
    - <@username#discriminator> -> <@user_id> (if user found in guild)
    - <@everyone> -> <@everyone>
    - <@roleName> -> <@roleName> (if role found in guild)

    Mentions that cannot be resolved or do not match these formats are left unchanged.

    Args:
        text: The input string potentially containing mentions.
        guild: The discord.Guild context for user/role lookups, or None if unavailable.

    Returns:
        The text with recognized mentions resolved.
    """
    if not text:
        return ""

    # Regex to find any content enclosed in <@...>
    # It captures the full mention in group 0 and the inner content in group 2
    mention_pattern = r"(<@([^>]+)>)"

    replacer_with_guild = partial(_mention_replacer, guild=guild)

    resolved_text = re.sub(mention_pattern, replacer_with_guild, text)

    return resolved_text

def get_all_roles_string(guild):
    """
    Returns a string listing all available roles in the guild for the model.
    If no roles, returns '(No roles.)'
    """
    if not guild or not hasattr(guild, "roles"):
        return "(No roles.)"
    # Exclude @everyone (default role)
    roles = [role.name for role in guild.roles if role.name != "@everyone"]
    if not roles:
        return "(No roles.)"
    return "\n".join(f"• {role}" for role in roles)

def resolve_mentions(content, message):
    """
    Resolves @username#discriminator to <@user_id> for pinging, @role to <@&role_id>, and @here to <@here>.
    Leaves as plain text if not found. User ID mentions (<@user_id>) are left as is.
    """
    guild = getattr(message, "guild", None)
    if not guild or not content:
        return content

def replace_mentions_with_username_discriminator(content, guild):
    """
    Convert <@user_id> mentions to @username#discriminator for AI input.
    Always includes discriminator if available, even if it's 0000.
    """
    def repl(match):
        user_id = int(match.group(1))
        member = guild.get_member(user_id)
        if member and hasattr(member, "discriminator"):
            # Always include discriminator, even if 0000
            return f"@{member.name}#{member.discriminator}"
        elif member:
            # Fallback if somehow no discriminator attribute (shouldn't happen often)
            return f"@{member.name}"
        else:
            # Keep original mention if user not found in cache
            # Maybe return a placeholder instead? For now, keep original.
            print(f"[replace_mentions] Member with ID {user_id} not found in cache.")
            return f"<@{user_id}>" # Or potentially f"@UnknownUser(ID:{user_id})#????"
    return re.sub(r"<@!?([0-9]+)>", repl, content)

    # Replace @here with <@here>
    content = re.sub(r"@here\b", "<@here>", content)

    # Replace all @username#discriminator with <@user_id> if found
    def username_discrim_replacer(match):
        username, discrim = match.group(1), match.group(2)
        member = discord.utils.get(guild.members, name=username, discriminator=discrim)
        if member:
            return f"<@{member.id}>"
        else:
            return match.group(0)  # Leave as is if not found

    content = re.sub(r"@([A-Za-z0-9_]{2,32})#(\d{1,4})", username_discrim_replacer, content)

    # Replace @role with <@&role_id> if role exists (no # in mention)
    def role_replacer(match):
        role_name = match.group(1)
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            return f"<@&{role.id}>"
        else:
            return match.group(0)  # Leave as is if not found

    # Only match @something that is not followed by # (not a username#discriminator)
    content = re.sub(r"@([A-Za-z0-9_ ]{2,32})(?!#)", role_replacer, content)

    return content
