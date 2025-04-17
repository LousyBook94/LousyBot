import unittest
from unittest.mock import MagicMock
import discord
from src.mention_utils import resolve_discord_mentions, parse_admin_file

class TestMentionUtils(unittest.TestCase):
    def setUp(self):
        # Create a mock guild with test members and roles
        self.guild = MagicMock(spec=discord.Guild)
        
        # Mock members
        member1 = MagicMock()
        member1.id = 123456789012345678
        member1.name = "TestUser"
        member1.discriminator = "1234"
        
        member2 = MagicMock()
        member2.id = 987654321098765432
        member2.name = "AnotherUser"
        member2.discriminator = "5678"
        
        self.guild.members = [member1, member2]
        
        # Mock roles
        role1 = MagicMock()
        role1.name = "Admin"
        role1.id = 111111111111111111
        
        role2 = MagicMock()
        role2.name = "Moderator"
        role2.id = 222222222222222222
        
        self.guild.roles = [role1, role2]

    def test_resolve_user_id_mention(self):
        text = "Hello <@123456789012345678>!"
        result = resolve_discord_mentions(text, self.guild)
        self.assertEqual(result, "Hello <@123456789012345678>!")

    def test_resolve_username_discriminator_mention(self):
        text = "Hello <@TestUser#1234>!"
        result = resolve_discord_mentions(text, self.guild)
        self.assertEqual(result, "Hello <@123456789012345678>!")

    def test_resolve_role_mention(self):
        text = "Hello <@Admin>!"
        result = resolve_discord_mentions(text, self.guild)
        self.assertEqual(result, "Hello @Admin!")

    def test_resolve_everyone_mention(self):
        text = "Hello <@everyone>!"
        result = resolve_discord_mentions(text, self.guild)
        self.assertEqual(result, "Hello @everyone!")

    def test_invalid_mention_format(self):
        text = "Hello <@InvalidUser>!"
        result = resolve_discord_mentions(text, self.guild)
        self.assertEqual(result, "Hello <@InvalidUser>!")

    def test_parse_admin_file(self):
        # Create a temporary admin.txt file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write("TestUser#1234\n")
            tmp.write("123456789012345678\n")
            tmp.write("InvalidLine\n")
            tmp_path = tmp.name
        
        valid_admins, errors, _ = parse_admin_file(tmp_path)
        self.assertEqual(len(valid_admins), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("TestUser#1234", valid_admins)
        self.assertIn("123456789012345678", valid_admins)
        self.assertIn("InvalidLine", errors[0])

if __name__ == "__main__":
    unittest.main()