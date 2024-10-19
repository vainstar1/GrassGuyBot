import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests
import datetime
import pytz
import json
import os

class StreamsCog(commands.Cog):
    
    twitch_group = app_commands.Group(name="twitch", description="Configure your Twitch settings.")

    def __init__(self, client: commands.Bot):
        self.client = client
        self.config_file = "stream_config.json"
        self.sent_streams = {}
        self.notifications_active = True

        self.TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
        self.TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
        self.TWITCH_REFRESH_TOKEN = os.getenv('TWITCH_REFRESH_TOKEN')
        self.TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

        self.token_expiry = datetime.datetime.utcnow()
        self.refresh_token_task.start()
        self.automatic_stream_check.start()

    def get_server_config(self, guild_id):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                config = json.load(file)
            return config.get(str(guild_id), {})
        return {}

    def set_server_config(self, guild_id, role_id, stream_channel_id, game_id, notifications_active=None):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                config = json.load(file)
        else:
            config = {}

        if str(guild_id) not in config:
            config[str(guild_id)] = {'notifications_active': True} 

        if notifications_active is not None:
            config[str(guild_id)]['notifications_active'] = notifications_active

        if game_id:
            if game_id not in config[str(guild_id)]:
                config[str(guild_id)][game_id] = {}

            config[str(guild_id)][game_id]['role_id'] = role_id
            config[str(guild_id)][game_id]['stream_channel_id'] = stream_channel_id

        with open(self.config_file, 'w') as file:
            json.dump(config, file, indent=4)

    def remove_server_config(self, guild_id, game_id):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                config = json.load(file)
        else:
            config = {}

        if str(guild_id) in config and game_id in config[str(guild_id)]:
            del config[str(guild_id)][game_id]

            if not config[str(guild_id)]:
                del config[str(guild_id)]

            with open(self.config_file, 'w') as file:
                json.dump(config, file, indent=4)
            return True
        return False

    async def get_game_id_from_name(self, game_name):
        url = "https://api.twitch.tv/helix/games"
        headers = {
            "Client-ID": self.TWITCH_CLIENT_ID,
            "Authorization": "Bearer " + self.TWITCH_OAUTH_TOKEN
        }
        params = {
            "name": game_name
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            games = data["data"]
            if games:
                return games[0]["id"]
        else:
            print(f"Error fetching game ID: {response.status_code} - {response.text}")
        return None

    async def get_game_name_from_id(self, game_id):
        url = "https://api.twitch.tv/helix/games"
        headers = {
            "Client-ID": self.TWITCH_CLIENT_ID,
            "Authorization": "Bearer " + self.TWITCH_OAUTH_TOKEN
        }
        params = {
            "id": game_id
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            games = data["data"]
            if games:
                return games[0]["name"]
        else:
            print(f"Error fetching game name: {response.status_code} - {response.text}")
        return None

    async def get_user_profile_image(self, user_id):
        url = f"https://api.twitch.tv/helix/users"
        headers = {
            "Client-ID": self.TWITCH_CLIENT_ID,
            "Authorization": "Bearer " + self.TWITCH_OAUTH_TOKEN
        }
        params = {
            "id": user_id
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            users = data.get('data', [])
            if users:
                return users[0].get('profile_image_url')
        else:
            print(f"Error fetching user profile image: {response.status_code} - {response.text}")
        return None

    @twitch_group.command(name="setup", description="Set up streams with role, channel, and game.")
    @app_commands.describe(role="Choose the role to be pinged (optional)", channel="Select the channel for streams", game="Enter the Twitch game name or ID")
    async def setupstreams(self, interaction: discord.Interaction, game: str, channel: discord.TextChannel, role: discord.Role = None):

        await interaction.response.defer()

        if game.isdigit():
            game_id = game
        else:
            game_id = await self.get_game_id_from_name(game)
            if not game_id:
                await interaction.followup.send("Could not find game ID for the specified name.")
                return

        self.set_server_config(interaction.guild.id, role.id if role else None, channel.id, game_id)
        await interaction.followup.send(f"Stream setup complete. Role: {role.name if role else 'None'}, Channel: {channel.name}, Game ID: {game_id}")

    @twitch_group.command(name="view-settings", description="View the current stream settings.")
    async def viewsetups(self, interaction: discord.Interaction):
        await interaction.response.defer()

        config = self.get_server_config(interaction.guild.id)
        if not config or 'notifications_active' not in config:
            await interaction.followup.send("No stream settings found.")
            return

        embed = discord.Embed(title="Current Stream Settings", color=discord.Color.blue())
        embed.add_field(name="Notifications Active", value="Yes" if config['notifications_active'] else "No")

        for game_id, settings in config.items():
            if game_id == 'notifications_active':
                continue  # Skip the notifications_active field

            role_id = settings.get('role_id')
            channel_id = settings['stream_channel_id']
            role = interaction.guild.get_role(role_id) if role_id else None
            channel = interaction.guild.get_channel(channel_id)
            game_name = await self.get_game_name_from_id(game_id)

            embed.add_field(name=f"Game: {game_name} (ID: {game_id})", 
                            value=f"Role: {role.name if role else 'None'}\nChannel: {channel.name if channel else 'Unknown'}", 
                            inline=False)
            embed.add_field(name="---", value="", inline=False)

        await interaction.followup.send(embed=embed)

    @twitch_group.command(name="remove-setting", description="Remove a stream setting.")
    @app_commands.describe(game="Enter the Twitch game name or ID to remove")
    async def removesetup(self, interaction: discord.Interaction, game: str):

        await interaction.response.defer()

        if game.isdigit():
            game_id = game
        else:
            game_id = await self.get_game_id_from_name(game)
            if not game_id:
                await interaction.followup.send("Could not find game ID for the specified name.")
                return

        if self.remove_server_config(interaction.guild.id, game_id):
            await interaction.followup.send(f"Removed stream setting for Game ID: {game_id}")
        else:
            await interaction.followup.send("Stream setting for the specified game not found.")

    @twitch_group.command(name="update-setting", description="Update the role or channel for a specific game.")
    @app_commands.describe(game="Enter the Twitch game name or ID", role="New role to be pinged (optional)", channel="New channel for streams (optional)")
    async def updatesetup(self, interaction: discord.Interaction, game: str, role: discord.Role = None, channel: discord.TextChannel = None):

        await interaction.response.defer()

        if game.isdigit():
            game_id = game
        else:
            game_id = await self.get_game_id_from_name(game)
            if not game_id:
                await interaction.followup.send("Could not find game ID for the specified name.")
                return

        config = self.get_server_config(interaction.guild.id)
        if not config or game_id not in config:
            await interaction.followup.send("Stream setting for the specified game not found.")
            return

        updated = False
        if role:
            config[game_id]['role_id'] = role.id
            updated = True
        if channel:
            config[game_id]['stream_channel_id'] = channel.id
            updated = True

        if updated:
            self.set_server_config(interaction.guild.id, config[game_id]['role_id'], config[game_id]['stream_channel_id'], game_id)
            await interaction.followup.send(f"Stream setting updated for Game ID: {game_id}. Role and/or channel has been changed.")
        else:
            await interaction.followup.send("No changes were made.")

    @twitch_group.command(name="toggle-notifications", description="Turn Twitch notifications on or off.")
    @app_commands.describe(notifications_active="Set to True to receive Twitch notifications, False to disable.")
    async def togglenotifications(self, interaction: discord.Interaction, notifications_active: bool):
        await interaction.response.defer()

        config = self.get_server_config(interaction.guild.id)

        if 'notifications_active' not in config:
            config['notifications_active'] = True 

        config['notifications_active'] = notifications_active
    
        self.set_server_config(interaction.guild.id, None, None, None, notifications_active=config['notifications_active']) 

        status = "active" if config['notifications_active'] else "inactive"
        await interaction.followup.send(f"Stream notifications are now {status}.")

    @tasks.loop(minutes=30)
    async def refresh_token_task(self):
        self.refresh_twitch_token()

    @tasks.loop(seconds=2)
    async def automatic_stream_check(self):
        if not self.notifications_active:
            return

        for guild in self.client.guilds:
            config = self.get_server_config(guild.id)
            if not config or not config.get('notifications_active', True):
                continue

            if datetime.datetime.utcnow() > self.token_expiry:
                self.refresh_twitch_token()

            for game_id, settings in config.items():
                if isinstance(settings, dict):
                    stream_channel_id = settings.get('stream_channel_id')
                    role_id = settings.get('role_id')
                    stream_channel = guild.get_channel(stream_channel_id)
                    role = guild.get_role(role_id) if role_id else None

                    streams = await self.check_twitch_streams(game_id)
                    for stream in streams:
                        stream_id = stream['id']
                        if stream_id not in self.sent_streams:
                            stream_link = f"https://www.twitch.tv/{stream['user_login']}"
                            thumbnail_url = stream.get('thumbnail_url', '').replace('{width}', '1920').replace('{height}', '1080')
                            user_name = stream['user_name']
                            profile_image_url = await self.get_user_profile_image(stream['user_id'])

                            game_box_art_url = f"https://static-cdn.jtvnw.net/ttv-boxart/{game_id}_IGDB-90x120.jpg"

                            start_time_utc = datetime.datetime.strptime(stream['started_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                            local_tz = pytz.timezone('America/New_York')  
                            start_time_local = start_time_utc.astimezone(local_tz) 
                            unix_timestamp = int(start_time_local.timestamp())

                            current_time = datetime.datetime.now(local_tz)  
                            uptime_duration = current_time - start_time_local
                            hours, remainder = divmod(int(uptime_duration.total_seconds()), 3600)
                            minutes, _ = divmod(remainder, 60)
                            uptime = f"{hours}h {minutes}m"

                            embed = discord.Embed(
                                title=stream['title'],
                                url=stream_link,
                                description=f"{user_name} is streaming {await self.get_game_name_from_id(game_id)} with {stream['viewer_count']} viewers.\n[Watch]({stream_link})",
                                color=discord.Color.purple()
                            )
                            embed.add_field(name="Uptime", value=uptime, inline=True)
                            embed.add_field(name="Language", value=stream.get('language', 'Unknown'), inline=True)
                            embed.add_field(name="Started at", value=f"<t:{unix_timestamp}:f>", inline=True)
                            embed.set_thumbnail(url=game_box_art_url)
                            embed.set_image(url=thumbnail_url) 
                            embed.set_author(name=user_name, icon_url=profile_image_url)
                            embed.set_footer(text="Powered by Twitch API")

                            if stream_channel:
                                await stream_channel.send(content=role.mention if role else '', embed=embed)

                            self.sent_streams[stream_id] = True

    def refresh_twitch_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.TWITCH_REFRESH_TOKEN,
            "client_id": self.TWITCH_CLIENT_ID,
            "client_secret": self.TWITCH_CLIENT_SECRET
        }
        response = requests.post(url, params=params)
        if response.status_code == 200:
            data = response.json()
            self.TWITCH_OAUTH_TOKEN = data["access_token"]
            self.token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=data["expires_in"])
        else:
            print(f"Error refreshing token: {response.status_code} - {response.text}")

    async def check_twitch_streams(self, game_id):
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-ID": self.TWITCH_CLIENT_ID,
            "Authorization": "Bearer " + self.TWITCH_OAUTH_TOKEN
        }
        params = {
            "game_id": game_id,
            "type": "live"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data["data"]
        else:
            print(f"Error fetching streams: {response.status_code} - {response.text}")
        return []

async def setup(client: commands.Bot):
    await client.add_cog(StreamsCog(client))
