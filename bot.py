import os
import random
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

discord_token = os.getenv("DISCORD_TOKEN")
channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
intents = discord.Intents.all()
client = discord.Client(intents=intents)

media_folder = "media"
os.makedirs(media_folder, exist_ok=True)

desc_folder = "desc"
os.makedirs(desc_folder, exist_ok=True)


def get_file_type(file_path):
    if not os.path.exists(file_path):
        return 'unknown'

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.heif'}
    video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'}

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in image_extensions:
        return 'image'
    elif file_extension in video_extensions:
        return 'video'
    else:
        return 'unknown'

def resize(image_path):
    image = Image.open(image_path)
    width, height = image.size

    new_width = width
    new_height = height

    if width > height:
        if width/height > 1.91:
            new_width = width
            new_height = width / 1.91
    else:
        if height/width > 1.2:
            new_width = height / 1.2
            new_height = height

    new_width = int(new_width)
    new_height = int(new_height)

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
    image_files = glob.glob(os.path.join(media_folder, '*'))

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

def get_random_post_time():
    now = datetime.datetime.now()
    today = now.date()

    if now.time() > datetime.time(19, 0):
        today = today + datetime.timedelta(days=1)

    start_seconds = 8 * 3600
    end_seconds = 19 * 3600
    random_seconds = random.randint(start_seconds, end_seconds)

    random_time = datetime.datetime.combine(today, datetime.time(0, 0)) + datetime.timedelta(seconds=random_seconds)
    return random_time

async def schedule_next_post():
    global next_post_time

    next_post_time = get_random_post_time()
    channel = client.get_channel(channel_id)

    if channel:
        await channel.send(f"Next post scheduled for: {next_post_time.strftime('%Y-%m-%d %H:%M:%S')}")

async def scheduler_loop():
    global next_post_time

    await schedule_next_post()

    while True:
        try:
            now = datetime.datetime.now()

            if next_post_time and now >= next_post_time:
                await post_image_to_instagram()
                await schedule_next_post()

            await asyncio.sleep(60)

        except Exception as e:
            channel = client.get_channel(channel_id)
            if channel:
                await channel.send(f"Scheduler error: {str(e)}")
            await asyncio.sleep(60)

@client.event
async def on_ready():
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send("Bot is ready and connected to Instagram !")
    else:
        print("Failed to connect to discord.")
    try:
        cl.login(username, password)
    except Exception as e:
        await channel.send("Instagram login failed : " + str(e))
    scheduler_task = asyncio.create_task(scheduler_loop())

@client.event
async def on_message(message):
    if message.channel.id == channel_id and message.author != client.user:
        if message.content == "!dump":
            tot, tot_img, tot_vid = 0, 0, 0
            msg_img, msg_vid = "", ""
            if len(os.listdir(media_folder)) > 0:
                for file in os.listdir(media_folder):
                    if get_file_type(os.path.join(media_folder, file)) == "image":
                        msg_img += f"{file}\n"
                        tot_img += 1
                    elif get_file_type(os.path.join(media_folder, file)) == "video":
                        msg_vid += f"{file}\n"
                        tot_vid += 1
                msg_img += f"Total images : {tot_img}\n"
                msg_vid += f"Total videos : {tot_vid}\n"
                msg = msg_img + msg_vid
                await message.channel.send(msg)
            else:
                await message.channel.send("No media remaining !")

        if message.content == "!dump_img":
            tot = 0
            msg = ""
            if len(os.listdir(media_folder)) > 0:
                for file in os.listdir(media_folder):
                    if get_file_type(os.path.join(media_folder, file)) == "image":
                        msg += f"{file}\n"
                        tot += 1
                msg += f"Total : {tot}\n"
                await message.channel.send(msg)
            else:
                await message.channel.send("No images remaining !")

        if message.channel.id == channel_id and message.author != client.user:
            if message.content == "!dump_vid":
                tot = 0
                msg = ""
                if len(os.listdir(media_folder)) > 0:
                    for file in os.listdir(media_folder):
                        if get_file_type(os.path.join(media_folder, file)) == "video":
                            msg += f"{file}\n"
                            tot += 1
                    msg += f"Total : {tot}\n"
                    await message.channel.send(msg)
                else:
                    await message.channel.send("No videos remaining !")

        if message.content == "!dump_txt":
            msg = ""
            if len(os.listdir(desc_folder)) > 0:
                for file in os.listdir(desc_folder):
                    msg += f"{file}\n"
                msg += f"Total : {len(os.listdir(desc_folder))}\n"
                await message.channel.send(msg)
            else:
                await message.channel.send("No images remaining !")

        if message.content == "!delete_all":
            for image in os.listdir(media_folder):
                os.remove(os.path.join(media_folder, image))
            await message.channel.send("Deleted all images !")
            for image in os.listdir(desc_folder):
                os.remove(os.path.join(desc_folder, image))
            await message.channel.send("Deleted all descriptions !")

        if len(message.content.split()) == 2 and "!delete" == message.content.split()[0]:
            if len(os.listdir(media_folder)) > 0:
                filename = message.content.split(" ")[1]
                if os.path.exists(os.path.join(media_folder, filename)):
                    os.remove(os.path.join(media_folder, filename))
                    os.remove(os.path.join(desc_folder, filename.split(".")[0] + ".txt"))
                    await message.channel.send(f"Deleted {filename}")
                else:
                    await message.channel.send("Image not found !")
            else:
                await message.channel.send("No image remaining !")

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type.startswith('image/'):
                    media_path = os.path.join(media_folder, attachment.filename)
                    await attachment.save(media_path)
                    await message.channel.send(f"Image {attachment.filename} saved to folder")
                    desc_name = os.path.splitext(os.path.basename(media_path))[0] + ".txt"
                    desc_path = os.path.join(desc_folder, desc_name)
                    with open(desc_path, "w") as desc:
                        desc.write(message.content)
                    await message.channel.send("Description saved to folder")
                    w1, h1, w2, h2 = resize(media_path)
                    await message.channel.send(f"Resized image from {w1}x{h1} to {w2}x{h2}")
                elif attachment.content_type.startswith('video/'):
                    media_path = os.path.join(media_folder, attachment.filename)
                    await attachment.save(media_path)
                    await message.channel.send(f"Video {attachment.filename} saved to folder")
                    desc_name = os.path.splitext(os.path.basename(media_path))[0] + ".txt"
                    desc_path = os.path.join(desc_folder, desc_name)
                    with open(desc_path, "w") as desc:
                        desc.write(message.content)
                    await message.channel.send("Description saved to folder")

client.run(discord_token)
