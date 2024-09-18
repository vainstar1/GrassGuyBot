import discord
from discord.ext import commands, tasks
from discord import app_commands
import os

<<<<<<<<<<<<<<  ✨ Codeium Command 🌟  >>>>>>>>>>>>>>>>
class PracticeCode(commands.Cog):
	
	practice = app_commands.group(name="practice", description="Learning Discord bots and Python, ignore!")

	def __init__(self, client: commands.Bot):
		self.client = client
	def __init__(self, client: commands.Bot)
	self.client = client

	@practice.command(name="whatever", description="im learning how to code")
	@app_commands.describe(number="choose number between 1-3")
	async def whatever(self, interaction: discord.Interaction, number: int):
		if number != 3:
			await interaction.response.send_message(f"Sorry, {number} is not correct. The correct answer is 3.")
		else:
			await interaction.response.send_message(f"Yay, {number} is correct! The answer is indeed 3.")
