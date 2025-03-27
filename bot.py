import os
import random
import schedule
from instagrapi import Client
from dotenv import load_dotenv
import discord
import asyncio
import glob
import datetime
from PIL import Image

load_dotenv()

cl = Client()

username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")
cl.login(username, password)

discord_token = os.getenv("DISCORD_TOKEN")
channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
intents = discord.Intents.all()
client = discord.Client(intents=intents)

image_folder = "img"
os.makedirs(image_folder, exist_ok=True)

desc_folder = "desc"
os.makedirs(desc_folder, exist_ok=True)

def resize(image_path):
    image = Image.open(image_path)

    width, height = image.size
    if width > height:
        target_ratio = (1.91, 1)
    else:
        target_ratio = (4, 5)
    target_width, target_height = target_ratio

    current_ratio = width / height
    target_ratio_value = target_width / target_height

    if current_ratio > target_ratio_value:
        new_width = width
        new_height = width/target_width
    elif current_ratio < target_ratio_value:
        new_width = height/target_height
        new_height = height
    else:
        new_width = width
        new_height = height

    if new_width != width or new_height != height:
        new_image = Image.new("RGB", (new_width, new_height), "white")

        left = (new_width - width) // 2
        top = (new_height - height) // 2

        new_image.paste(image, (left, top))

        new_image.save(image_path)

        return width, height, new_image.width, new_image.height
    else:
        return width, height, width, height

async def post_image_to_instagram():
    channel = client.get_channel(channel_id)
    image_files = glob.glob(os.path.join(image_folder, '*'))

    if image_files:
        image_path = random.choice(image_files)
        desc_name = os.path.splitext(os.path.basename(image_path))[0] + ".txt"
        desc_path = os.path.join(desc_folder, desc_name)

        if os.path.exists(desc_path):
            with open(desc_path, "r") as desc_file:
                description = desc_file.read()

            cl.photo_upload(image_path, description)
            await channel.send(f"Posted {image_path} to Instagram with description from {desc_path}")

            os.remove(image_path)
            os.remove(desc_path)
            await channel.send(f"Deleted {image_path} and {desc_path}")
    else:
        await channel.send("No image remaining !")

def schedule_random_post():
    schedule.clear()

    start_time = datetime.time(8, 0)
    end_time = datetime.time(19, 0)
    random_time = datetime.datetime.combine(datetime.date.today(), start_time) + datetime.timedelta(
        seconds=random.randint(0, (datetime.datetime.combine(datetime.date.today(), end_time) - datetime.datetime.combine(datetime.date.today(), start_time)).seconds)
    )

    schedule.every().day.at(random_time.strftime("%H:%M")).do(lambda: asyncio.run_coroutine_threadsafe(post_image_to_instagram(), client.loop))
    schedule.every().day.at("07:00").do(lambda: asyncio.run_coroutine_threadsafe(schedule_random_post_wrapper(), client.loop))

async def schedule_random_post_wrapper():
    schedule_random_post()

schedule_random_post()

async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

@client.event
async def on_ready():
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send("Bot is ready !")
    client.loop.create_task(run_scheduler())

@client.event
async def on_message(message):
    if message.channel.id == channel_id and message.author != client.user:
        if message.content == "!dump":
            msg = ""
            if len(os.listdir(image_folder)) > 0:
                for file in os.listdir(image_folder):
                    msg += f"{file}\n"
                msg += f"Total : {len(os.listdir(image_folder))}\n"
                await message.channel.send(msg)
            else:
                await message.channel.send("No images remaining !")

        if message.content == "!dump_txt":
            msg = ""
            if len(os.listdir(desc_folder)) > 0:
                for file in os.listdir(desc_folder):
                    msg += f"{file}\n"
                msg += f"Total : {len(os.listdir(desc_folder))}\n"
                await message.channel.send(msg)
            else:
                await message.channel.send("No images remaining !")

        if len(message.content.split()) == 2 and "!delete" == message.content.split()[0]:
            if len(os.listdir(image_folder)) > 0:
                filename = message.content.split(" ")[1]
                if os.path.exists(os.path.join(image_folder, filename)):
                    os.remove(os.path.join(image_folder, filename))
                    os.remove(os.path.join(desc_folder, filename.split(".")[0] + ".txt"))
                    await message.channel.send(f"Deleted {filename}")
                else:
                    await message.channel.send("Image not found !")
            else:
                await message.channel.send("No image remaining !")

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type.startswith('image/'):
                    image_path = os.path.join(image_folder, attachment.filename)
                    await attachment.save(image_path)
                    await message.channel.send("Image saved to folder")
                    desc_name = os.path.splitext(os.path.basename(image_path))[0] + ".txt"
                    desc_path = os.path.join(desc_folder, desc_name)
                    with open(desc_path, "w") as desc:
                        desc.write(message.content)
                    await message.channel.send("Description saved to folder")
                    w1, h1, w2, h2 = resize(image_path)
                    await message.channel.send(f"Resized image from {w1}x{h1} to {w2}x{h2}")

client.run(discord_token)