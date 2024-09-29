import discord
from discord import app_commands
from discord.ext import commands
import re

class TranslateCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    cipher_map = {chr(i): f":MachineCipher{chr(i).upper()}:" for i in range(97, 123)}
    reverse_cipher_map = {v: k for k, v in cipher_map.items()}

    def to_plain_text(self, cipher_message):
        emote_pattern = r'<a?:MachineCipher([A-Z]):\d+>'
        translated_message = re.sub(emote_pattern, lambda m: self.reverse_cipher_map[f":MachineCipher{m.group(1)}:"], cipher_message)
        translated_message = re.sub(r'\s+', ' ', translated_message.strip()) 
        return translated_message

    def to_machine_cipher(self, plain_text):
        translated_message = ''.join(
            [self.cipher_map[char.lower()] if char.lower() in self.cipher_map else ' ' for char in plain_text]
        )
        return translated_message

    @app_commands.command(name="translate-to-english", description="Translates machine cipher text to plain text.")
    async def translate(self, interaction: discord.Interaction, cipher_text: str, ephemeral: bool = False):
        if not cipher_text:
            await interaction.response.send_message("Please provide a machine cipher text to translate!", ephemeral=ephemeral)
            return

        translated_message = self.to_plain_text(cipher_text)
        await interaction.response.send_message(translated_message, ephemeral=ephemeral)

    @app_commands.command(name="translate-to-cipher", description="Translates plain English text to machine cipher.")
    async def to_machine_cipher_command(self, interaction: discord.Interaction, plain_text: str, ephemeral: bool = False):
        if not plain_text:
            await interaction.response.send_message("Please provide a plain text to translate!", ephemeral=ephemeral)
            return

        translated_message = self.to_machine_cipher(plain_text)
        await interaction.response.send_message(translated_message, ephemeral=ephemeral)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(TranslateCog(client))
