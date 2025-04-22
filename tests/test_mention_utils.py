from unittest.mock import MagicMock
import discord
from src.mention_utils import replace_mentions, load_admins
import pytest

@pytest.fixture
def mock_guild():
    # Create a mock guild with test members and roles
    guild = MagicMock(spec=discord.Guild)
    
    # Mock members
    member1 = MagicMock()
    member1.id = 123456789012345678
    member1.name = "TestUser"
    member1.discriminator = "1234"
    
    member2 = MagicMock()
    member2.id = 987654321098765432
    member2.name = "AnotherUser"
    member2.discriminator = "5678"
    
    guild.members = [member1, member2]
    
    # Mock roles
    role1 = MagicMock()
    role1.name = "Admin"
    role1.id = 111111111111111111
    
    role2 = MagicMock()
    role2.name = "Moderator"
    role2.id = 222222222222222222
    
    guild.roles = [role1, role2]
    return guild

def test_resolve_user_id_mention(mock_guild):
    text = "Hello <@123456789012345678>!"
    result = replace_mentions(text, mock_guild)
    assert result == "Hello <@123456789012345678>!"

def test_resolve_username_discriminator_mention(mock_guild):
    text = "Hello <@TestUser#1234>!"
    result = replace_mentions(text, mock_guild)
    assert result == "Hello <@123456789012345678>!"

def test_resolve_role_mention(mock_guild):
    text = "Hello <@Admin>!"
    result = replace_mentions(text, mock_guild)
    assert result == "Hello @Admin!"

def test_resolve_everyone_mention(mock_guild):
    text = "Hello <@everyone>!"
    result = replace_mentions(text, mock_guild)
    assert result == "Hello @everyone!"

def test_invalid_mention_format(mock_guild):
    text = "Hello <@InvalidUser>!"
    result = replace_mentions(text, mock_guild)
    assert result == "Hello <@InvalidUser>!"

def test_parse_admin_file():
    # Create a temporary admin.txt file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp.write("TestUser#1234\n")
        tmp.write("123456789012345678\n")
        tmp.write("InvalidLine\n")
        tmp_path = tmp.name
    
    valid_admins, errors, _ = load_admins(tmp_path)
    assert len(valid_admins) == 2
    assert len(errors) == 1
    assert "TestUser#1234" in valid_admins
    assert "123456789012345678" in valid_admins
    assert "InvalidLine" in errors[0]