import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class addrole(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.fixed_message_id = 1280264066174156943
        self.admin_role_id = 1280250785384632453
        self.reaction_roles = self.load_reaction_roles()

    def load_reaction_roles(self):
        if os.path.exists('reaction_roles.json'):
            try:
                with open('reaction_roles.json', 'r') as file:
                    return json.load(file)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_reaction_roles(self):
        with open('reaction_roles.json', 'w') as file:
            json.dump(self.reaction_roles, file, indent=4)

    async def cog_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if guild is None:
            return False
        admin_role = guild.get_role(self.admin_role_id)
        return admin_role in interaction.user.roles

    @app_commands.command(name="addreactionrole", description="Add a reaction role.")
    async def addreactionrole(self, interaction: discord.Interaction, emoji: str, role: discord.Role):
        if not await self.cog_check(interaction):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        if str(self.fixed_message_id) not in self.reaction_roles:
            self.reaction_roles[str(self.fixed_message_id)] = {}
        self.reaction_roles[str(self.fixed_message_id)][emoji] = role.id
        self.save_reaction_roles()

        # Fetch the message and add the reaction
        channel = interaction.channel
        try:
            message = await channel.fetch_message(self.fixed_message_id)
            await message.add_reaction(emoji)
        except discord.NotFound:
            await interaction.response.send_message("Message not found.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("Missing permissions to react to the message.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            return

        await interaction.response.send_message(f"Added reaction role: {emoji} -> {role.name} and reacted to the message.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        if message_id in self.reaction_roles:
            if emoji in self.reaction_roles[message_id]:
                guild = self.client.get_guild(payload.guild_id)
                if guild is None:
                    return

                member = guild.get_member(payload.user_id)
                role_id = self.reaction_roles[message_id][emoji]
                role = guild.get_role(role_id)

                if member and role:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        if message_id in self.reaction_roles:
            if emoji in self.reaction_roles[message_id]:
                guild = self.client.get_guild(payload.guild_id)
                if guild is None:
                    return

                member = guild.get_member(payload.user_id)
                role_id = self.reaction_roles[message_id][emoji]
                role = guild.get_role(role_id)

                if member and role:
                    await member.remove_roles(role)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(addrole(client))