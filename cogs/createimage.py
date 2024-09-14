import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io

class createimage(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
    
    @app_commands.command(name="createimage", description="Creates a goofy ahh image of your text.")
    async def createimage(self, interaction: discord.Interaction, text: str):
        frames = []
        width, height = 800, 200
        num_frames = 30
        initial_font_size = 40
        font_path = "arial.ttf"

        def get_text_size(draw, text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            return text_width, text_height

        def wrap_text(draw, text, font, max_width):
            words = text.split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + word + " "
                test_width, _ = get_text_size(draw, test_line, font)

                if test_width <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "

            if current_line:
                lines.append(current_line.strip())

            return lines

        font_size = initial_font_size
        while True:
            font = ImageFont.truetype(font_path, font_size)
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            wrapped_text = wrap_text(draw, text, font, width - 20)
            total_text_height = sum(get_text_size(draw, line, font)[1] for line in wrapped_text)
            if total_text_height <= height - 20:
                break
            font_size -= 1

        top_margin = (height - total_text_height) // 2

        for i in range(num_frames):
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)

            for y in range(height):
                r = int(255 * (y / height))
                g = 0
                b = int(255 * (1 - (y / height)))

                draw.line([(0, y), (width, y)], fill=(r, g, b))

            shift = 255 * i // num_frames
            color = (shift % 255, (shift * 2) % 255, (shift * 3) % 255)

            current_y = top_margin
            for line in wrapped_text:
                text_width, text_height = get_text_size(draw, line, font)
                draw.text(((width - text_width) // 2, current_y), line, font=font, fill=color)
                current_y += text_height

            frames.append(image)

        image_bytes = io.BytesIO()
        frames[0].save(image_bytes, format='GIF', save_all=True, append_images=frames[1:], duration=100, loop=0)
        image_bytes.seek(0)

        await interaction.response.send_message(file=discord.File(image_bytes, 'animated_text.gif'))

async def setup(client:commands.Bot) -> None:
    await client.add_cog(createimage(client))
