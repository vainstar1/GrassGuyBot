import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import datetime
import pytz
import os

class StreamsCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.game_id = "1287238118"
        self.sent_streams = {}
        self.stream_channel_id = 1280254057071771731
        self.role_id = 1280263697356296252
        self.stream_ping = f"<@&{self.role_id}>"

        self.TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
        self.TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
        self.TWITCH_REFRESH_TOKEN = os.getenv('TWITCH_REFRESH_TOKEN')
        self.TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

        self.token_expiry = datetime.datetime.utcnow()
        self.refresh_token_task.start()
        self.automatic_stream_check.start()

    @tasks.loop(minutes=30)
    async def refresh_token_task(self):
        self.refresh_twitch_token()

    @tasks.loop(seconds=2)
    async def automatic_stream_check(self):
        # Refresh token if expired
        if datetime.datetime.utcnow() > self.token_expiry:
            self.refresh_twitch_token()
        await self.send_streams_to_channels()

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
            self.TWITCH_OAUTH_TOKEN = data['access_token']
            self.TWITCH_REFRESH_TOKEN = data['refresh_token']
            self.token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=data['expires_in'])
            print("Twitch OAuth token refreshed successfully.")
        else:
            print(f"Error refreshing Twitch token: {response.status_code}")
            print("Response:", response.content)

    def get_active_streams_in_category(self, game_id, TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN):
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": "Bearer " + TWITCH_OAUTH_TOKEN
        }
        params = {
            "game_id": game_id
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()["data"]
        else:
            print("Error:", response.status_code)
            return []

    async def send_streams_to_channels(self):
        active_streams = self.get_active_streams_in_category(self.game_id, self.TWITCH_CLIENT_ID, self.TWITCH_OAUTH_TOKEN)

        for stream in active_streams:
            stream_id = stream['id']
            if stream_id not in self.sent_streams or not self.sent_streams[stream_id]:
                stream_link = f"https://www.twitch.tv/{stream['user_login']}"

                start_time = datetime.datetime.strptime(stream['started_at'], "%Y-%m-%dT%H:%M:%SZ")
                utc = pytz.utc
                est = pytz.timezone('America/New_York')
                start_time = utc.localize(start_time).astimezone(est)

                formatted_start_time = start_time.strftime("%m/%d/%Y, %I:%M %p")

                message = f"{self.stream_ping}\nTitle: {stream['title']}\nStream Started at: {formatted_start_time} EST\nViewer Count: {stream['viewer_count']}\nStream Link: {stream_link}\n-------------"
                channel = self.client.get_channel(self.stream_channel_id)
                if channel:
                    await channel.send(message)
                self.sent_streams[stream_id] = True
                print(f"Stream detected and sent: {stream['title']} - Viewer Count: {stream['viewer_count']}")
            else:
                if stream_id in self.sent_streams and not stream['type'] == 'live':
                    self.sent_streams[stream_id] = False

async def setup(client: commands.Bot) -> None:
    await client.add_cog(StreamsCog(client))
