import discord
import re
from discord import app_commands
from discord.ext import commands

class TwitterLinkReplacer(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.twitter_link_regex = re.compile(r'https:\/\/(?:twitter|x)\.com\/[a-zA-Z0-9]+\/status\/[a-zA-Z0-9]+')
        self.provider = "fxtwitter" 

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.client.user:
            return

        links = self.twitter_link_regex.findall(message.content)
        if links:
            # Prepare the modified message
            text = '\n'.join(link.replace('twitter.com', f'{self.provider}.com').replace('x.com', f'{self.provider}.com') for link in links)
            
            await message.channel.send(text, reference=message)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(TwitterLinkReplacer(client))
