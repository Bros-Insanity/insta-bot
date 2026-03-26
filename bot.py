import os
import random
from instagrapi import Client
from dotenv import load_dotenv
import discord
from discord import app_commands
import asyncio
import glob
import datetime
from PIL import Image
import hashlib
import imagehash
import json
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

cl = Client()

username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")

discord_token = os.getenv("DISCORD_TOKEN")
channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))

AUTO_SYNC_ON_STARTUP = os.getenv("AUTO_SYNC_ON_STARTUP", "false").lower() == "true"
PHASH_THRESHOLD = 10 # Max Hamming distance (0=identical, 64=opposite)

executor = ThreadPoolExecutor(max_workers=2)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

media_folder = "media"
os.makedirs(media_folder, exist_ok=True)

desc_folder = "desc"
os.makedirs(desc_folder, exist_ok=True)

hash_file = "image_hashes.json"

next_post_time = None


def load_hashes():
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            return json.load(f)
    return {}


def save_hashes(hashes):
    with open(hash_file, "w") as f:
        json.dump(hashes, f, indent=2)


def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_perceptual_hash(file_path):
    with Image.open(file_path) as img:
        return str(imagehash.phash(img))


def is_duplicate_image(file_path):
    hashes = load_hashes()
    file_type = get_file_type(file_path)

    if file_type == "image":
        try:
            new_phash = imagehash.hex_to_hash(calculate_perceptual_hash(file_path))
        except Exception as e:
            print(f"pHash error on {file_path}: {e}")
            return False, calculate_perceptual_hash(file_path)

        for key, stored in hashes.items():
            if not key.startswith("sha256:"):
                try:
                    stored_phash = imagehash.hex_to_hash(stored)
                    if abs(new_phash - stored_phash) <= PHASH_THRESHOLD:
                        return True, str(new_phash)
                except Exception:
                    continue

        return False, str(new_phash)

    else:
        file_hash = calculate_file_hash(file_path)
        sha_key = f"sha256:{file_hash}"
        if sha_key in hashes.values() or file_hash in hashes.values():
            return True, file_hash
        return False, file_hash


def add_image_hash(filename, file_hash):
    hashes = load_hashes()
    hashes[filename] = file_hash
    save_hashes(hashes)


def remove_image_hash(filename):
    hashes = load_hashes()
    if filename in hashes:
        del hashes[filename]
        save_hashes(hashes)


def sync_instagram_media_blocking():
    try:
        user_id = cl.user_id_from_username(username)

        medias = cl.user_medias(user_id, amount=0) # 0 = all media

        hashes = load_hashes()
        new_hashes = 0
        errors = 0
        temp_folder = "temp_instagram_sync"
        os.makedirs(temp_folder, exist_ok=True)

        for idx, media in enumerate(medias):
            try:
                downloaded_path = None

                if media.media_type == 1: # Photo
                    downloaded_path = cl.photo_download(media.pk, folder=temp_folder)
                elif media.media_type == 2: # Video
                    downloaded_path = cl.video_download(media.pk, folder=temp_folder)
                elif media.media_type == 8: # Album
                    resources = media.resources
                    for res_idx, resource in enumerate(resources):
                        try:
                            if resource.media_type == 1: # Photo in album
                                res_path = cl.photo_download(
                                    resource.pk, folder=temp_folder
                                )
                                res_hash = calculate_perceptual_hash(res_path)
                                is_dup = any(
                                    abs(imagehash.hex_to_hash(res_hash) - imagehash.hex_to_hash(h)) <= PHASH_THRESHOLD
                                    for h in hashes.values()
                                    if not h.startswith("sha256:")
                                )
                            elif resource.media_type == 2:  # Video in album
                                res_path = cl.video_download(
                                    resource.pk, folder=temp_folder
                                )
                                res_hash = calculate_file_hash(res_path)
                                is_dup = f"sha256:{res_hash}" in hashes.values()
                            else:
                                continue

                            hash_key = f"instagram_{media.pk}_{res_idx}"
                            if not is_dup:
                                hashes[hash_key] = res_hash
                                new_hashes += 1

                            if os.path.exists(res_path):
                                os.remove(res_path)
                        except Exception as e:
                            print(f"Error processing album resource {res_idx}: {e}")
                            errors += 1

                    continue
                else:
                    continue

                if downloaded_path and os.path.exists(downloaded_path):
                    if media.media_type == 1: # Photo
                        file_hash = calculate_perceptual_hash(downloaded_path)
                        is_dup = any(
                            abs(imagehash.hex_to_hash(file_hash) - imagehash.hex_to_hash(h)) <= PHASH_THRESHOLD
                            for h in hashes.values()
                            if not h.startswith("sha256:")
                        )
                    else: # Video
                        file_hash = calculate_file_hash(downloaded_path)
                        is_dup = f"sha256:{file_hash}" in hashes.values()

                    hash_key = f"instagram_{media.pk}"
                    if not is_dup:
                        hashes[hash_key] = file_hash
                        new_hashes += 1

                    os.remove(downloaded_path)

            except Exception as e:
                print(f"Error processing media {media.pk}: {e}")
                errors += 1
                continue

        save_hashes(hashes)

        if os.path.exists(temp_folder):
            for file in os.listdir(temp_folder):
                try:
                    os.remove(os.path.join(temp_folder, file))
                except:
                    pass
            try:
                os.rmdir(temp_folder)
            except:
                pass

        return True, new_hashes, len(hashes), len(medias), errors

    except Exception as e:
        print(f"Error in sync_instagram_media_blocking: {e}")
        return False, 0, 0, 0, 0


async def sync_instagram_posted_media(channel=None):
    try:
        if channel:
            await channel.send("Starting Instagram media sync...")
            await channel.send("This may take a while. The bot will remain responsive.")

        loop = asyncio.get_event_loop()
        success, new_hashes, total_hashes, total_posts, errors = (
            await loop.run_in_executor(executor, sync_instagram_media_blocking)
        )

        if channel:
            if success:
                await channel.send(
                    f"Instagram sync complete!\n"
                    f"Total posts processed: {total_posts}\n"
                    f"New hashes added: {new_hashes}\n"
                    f"Total hashes in database: {total_hashes}\n"
                    f"Errors encountered: {errors}"
                )
            else:
                await channel.send("Sync failed. Check console for details.")

        return success, new_hashes, total_hashes

    except Exception as e:
        if channel:
            await channel.send(f"Error syncing Instagram media: {str(e)}")
        print(f"Error in sync_instagram_posted_media: {e}")
        return False, 0, 0


def get_file_type(file_path):
    if not os.path.exists(file_path):
        return "unknown"

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".svg",
        ".ico",
        ".heic",
        ".heif",
    }
    video_extensions = {
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".mkv",
        ".m4v",
        ".3gp",
        ".ogv",
        ".ts",
        ".mts",
        ".m2ts",
    }

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in image_extensions:
        return "image"
    elif file_extension in video_extensions:
        return "video"
    else:
        return "unknown"


def resize(image_path):
    image = Image.open(image_path)
    width, height = image.size

    new_width = width
    new_height = height

    if width > height:
        if width / height > 1.91:
            new_width = width
            new_height = width / 1.91
    else:
        if height / width > 1.2:
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
    image_files = glob.glob(os.path.join(media_folder, "*"))

    if image_files:
        image_path = random.choice(image_files)
        filename = os.path.basename(image_path)
        desc_name = os.path.splitext(filename)[0] + ".txt"
        desc_path = os.path.join(desc_folder, desc_name)

        if os.path.exists(desc_path):
            with open(desc_path, "r") as desc_file:
                description = desc_file.read()

            try:
                loop = asyncio.get_event_loop()
                file_type = get_file_type(image_path)

                if file_type == "video":
                    await loop.run_in_executor(
                        executor, cl.video_upload, image_path, description
                    )
                else:
                    await loop.run_in_executor(
                        executor, cl.photo_upload, image_path, description
                    )

                await channel.send(f"Posted {filename} to Instagram")
            except Exception as e:
                await channel.send(f"Failed to post {filename}: {str(e)}")
                return

            remove_image_hash(filename)
            os.remove(image_path)
            os.remove(desc_path)
            await channel.send(f"Deleted {filename} and description")
    else:
        await channel.send("No image remaining!")


def get_random_post_time():
    now = datetime.datetime.now()
    today = now.date()

    start_seconds = 8 * 3600
    end_seconds = 19 * 3600
    now_seconds = now.hour * 3600 + now.minute * 60 + now.second

    if now_seconds >= end_seconds:
        today = today + datetime.timedelta(days=1)
        random_seconds = random.randint(start_seconds, end_seconds)
    else:
        min_seconds = max(start_seconds, now_seconds + 60)
        if min_seconds >= end_seconds:
            today = today + datetime.timedelta(days=1)
            random_seconds = random.randint(start_seconds, end_seconds)
        else:
            random_seconds = random.randint(min_seconds, end_seconds)

    return datetime.datetime.combine(today, datetime.time(0, 0)) + datetime.timedelta(seconds=random_seconds)


async def schedule_next_post():
    global next_post_time

    next_post_time = get_random_post_time()
    channel = client.get_channel(channel_id)

    if channel:
        await channel.send(
            f"Next post scheduled for: {next_post_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )


async def scheduler_loop():
    global next_post_time

    await schedule_next_post()

    while True:
        try:
            now = datetime.datetime.now()

            if (
                next_post_time
                and now >= next_post_time
                and len(os.listdir(media_folder)) > 0
            ):
                print(len(os.listdir(media_folder)))
                await post_image_to_instagram()
                await schedule_next_post()

            await asyncio.sleep(60)

        except Exception as e:
            channel = client.get_channel(channel_id)
            if channel:
                await channel.send(f"Scheduler error: {str(e)}")
            await asyncio.sleep(60)


@tree.command(name="dump", description="List all media files in the queue")
async def dump(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    tot_img, tot_vid = 0, 0
    msg_img, msg_vid = "", ""

    if len(os.listdir(media_folder)) > 0:
        for file in os.listdir(media_folder):
            if get_file_type(os.path.join(media_folder, file)) == "image":
                msg_img += f"{file}\n"
                tot_img += 1
            elif get_file_type(os.path.join(media_folder, file)) == "video":
                msg_vid += f"{file}\n"
                tot_vid += 1

        msg_img += f"Total images: {tot_img}\n"
        msg_vid += f"Total videos: {tot_vid}\n"
        msg = msg_img + msg_vid
        await interaction.response.send_message(msg)
    else:
        await interaction.response.send_message("No media remaining!")


@tree.command(name="dump_img", description="List all images in the queue")
async def dump_img(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    tot = 0
    msg = ""

    if len(os.listdir(media_folder)) > 0:
        for file in os.listdir(media_folder):
            if get_file_type(os.path.join(media_folder, file)) == "image":
                msg += f"{file}\n"
                tot += 1
        msg += f"Total: {tot}\n"
        await interaction.response.send_message(msg if msg else "No images remaining!")
    else:
        await interaction.response.send_message("No images remaining!")


@tree.command(name="dump_vid", description="List all videos in the queue")
async def dump_vid(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    tot = 0
    msg = ""

    if len(os.listdir(media_folder)) > 0:
        for file in os.listdir(media_folder):
            if get_file_type(os.path.join(media_folder, file)) == "video":
                msg += f"{file}\n"
                tot += 1
        msg += f"Total: {tot}\n"
        await interaction.response.send_message(msg if msg else "No videos remaining!")
    else:
        await interaction.response.send_message("No videos remaining!")


@tree.command(name="dump_txt", description="List all description files")
async def dump_txt(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    msg = ""

    if len(os.listdir(desc_folder)) > 0:
        for file in os.listdir(desc_folder):
            msg += f"{file}\n"
        msg += f"Total: {len(os.listdir(desc_folder))}\n"
        await interaction.response.send_message(msg)
    else:
        await interaction.response.send_message("No description files remaining!")


@tree.command(name="delete_all", description="Delete all media and description files")
async def delete_all(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    for image in os.listdir(media_folder):
        os.remove(os.path.join(media_folder, image))

    for desc in os.listdir(desc_folder):
        os.remove(os.path.join(desc_folder, desc))

    save_hashes({})

    await interaction.response.send_message("Deleted all media and description files!")


@tree.command(name="delete", description="Delete a specific media file")
@app_commands.describe(filename="The name of the file to delete")
async def delete(interaction: discord.Interaction, filename: str):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    if len(os.listdir(media_folder)) > 0:
        if os.path.exists(os.path.join(media_folder, filename)):
            os.remove(os.path.join(media_folder, filename))
            desc_file = filename.split(".")[0] + ".txt"
            desc_path = os.path.join(desc_folder, desc_file)
            if os.path.exists(desc_path):
                os.remove(desc_path)

            remove_image_hash(filename)

            await interaction.response.send_message(f"Deleted {filename}")
        else:
            await interaction.response.send_message("File not found!")
    else:
        await interaction.response.send_message("No media remaining!")


@tree.command(name="upload", description="Upload media with description")
@app_commands.describe(
    media="The image or video to upload",
    description="Description/caption for the media",
)
async def upload(
    interaction: discord.Interaction, media: discord.Attachment, description: str
):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    await interaction.response.defer()

    try:
        if media.content_type.startswith("image/"):
            media_path = os.path.join(media_folder, media.filename)
            await media.save(media_path)

            is_duplicate, file_hash = is_duplicate_image(media_path)
            if is_duplicate:
                os.remove(media_path)
                await interaction.followup.send(
                    f"Duplicate image detected! This image has already been uploaded.\n"
                    f"Hash: {file_hash[:16]}..."
                )
                return

            desc_name = os.path.splitext(os.path.basename(media_path))[0] + ".txt"
            desc_path = os.path.join(desc_folder, desc_name)
            with open(desc_path, "w") as desc_file:
                desc_file.write(description)

            w1, h1, w2, h2 = resize(media_path)
            img_size_info = (
                " and resized from {w1}x{h1} to {w2}x{h2}."
                if h1 == h2 and w1 == w2
                else "."
            )

            add_image_hash(media.filename, file_hash)

            await interaction.followup.send(
                f"Image {media.filename} saved" + img_size_info + "\n"
                f"Description saved to {desc_name}\n"
                f"Hash: {file_hash[:16]}..."
            )

        elif media.content_type.startswith("video/"):
            media_path = os.path.join(media_folder, media.filename)
            await media.save(media_path)

            is_duplicate, file_hash = is_duplicate_image(media_path)
            if is_duplicate:
                os.remove(media_path)
                await interaction.followup.send(
                    f"Duplicate video detected! This video has already been uploaded.\n"
                    f"Hash: {file_hash[:16]}..."
                )
                return

            desc_name = os.path.splitext(os.path.basename(media_path))[0] + ".txt"
            desc_path = os.path.join(desc_folder, desc_name)
            with open(desc_path, "w") as desc_file:
                desc_file.write(description)

            add_image_hash(media.filename, file_hash)

            await interaction.followup.send(
                f"Video {media.filename} saved\n"
                f"Description saved to {desc_name}\n"
                f"Hash: {file_hash[:16]}..."
            )
        else:
            await interaction.followup.send(
                "Invalid file type. Please upload an image or video."
            )

    except Exception as e:
        await interaction.followup.send(f"Error uploading media: {str(e)}")


@tree.command(name="next_post", description="Show when the next post is scheduled")
async def next_post(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    if next_post_time:
        await interaction.response.send_message(
            f"Next post scheduled for: {next_post_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        await interaction.response.send_message("No post currently scheduled.")


@tree.command(
    name="sync_instagram",
    description="Sync all posted Instagram media to prevent duplicates",
)
async def sync_instagram(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Starting Instagram sync... This will run in the background and may take several minutes."
    )

    asyncio.create_task(sync_instagram_posted_media(interaction.channel))


@tree.command(name="hash_stats", description="Show statistics about stored hashes")
async def hash_stats(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    hashes = load_hashes()

    instagram_hashes = sum(1 for key in hashes.keys() if key.startswith("instagram_"))
    local_hashes = len(hashes) - instagram_hashes

    await interaction.response.send_message(
        f"Hash Database Statistics:\n\n"
        f"Instagram posts: {instagram_hashes}\n"
        f"Local files: {local_hashes}\n"
        f"Total hashes: {len(hashes)}"
    )


@tree.command(name="sync_commands", description="Force re-sync Discord slash commands")
async def sync_commands(interaction: discord.Interaction):
    if interaction.channel_id != channel_id:
        await interaction.response.send_message(
            "This command can only be used in the designated channel.", ephemeral=True
        )
        return

    await interaction.response.defer()

    try:
        synced = await tree.sync()
        await interaction.followup.send(f"Synced {len(synced)} commands successfully!")
    except Exception as e:
        await interaction.followup.send(f"Failed to sync commands: {str(e)}")


@client.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Logged in as {client.user}")
        print(f"Synced {len(synced)} slash commands:")
        for cmd in synced:
            print(f"  - /{cmd.name}: {cmd.description}")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    channel = client.get_channel(channel_id)
    if channel:
        await channel.send("Bot is ready and connected!")
    else:
        print("Failed to connect to Discord channel.")

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, cl.login, username, password)
        print("Instagram login successful")
        if channel:
            await channel.send("Instagram login successful!")

            if AUTO_SYNC_ON_STARTUP:
                await channel.send("Auto-sync is enabled. Starting background sync...")
                asyncio.create_task(sync_instagram_posted_media(channel))
            else:
                await channel.send(
                    "Auto-sync is disabled. Use `/sync_instagram` to manually sync.\n"
                    "To enable auto-sync, set `AUTO_SYNC_ON_STARTUP=true` in your .env file."
                )

    except Exception as e:
        if channel:
            await channel.send(f"Instagram login failed: {str(e)}")
        print(f"Instagram login failed: {str(e)}")

    asyncio.create_task(scheduler_loop())


# Mssage handler for attachments sent without slash command
@client.event
async def on_message(message):
    if message.channel.id == channel_id and message.author != client.user:
        if message.attachments and not message.content.startswith("/"):
            for attachment in message.attachments:
                if attachment.content_type.startswith("image/"):
                    media_path = os.path.join(media_folder, attachment.filename)
                    await attachment.save(media_path)

                    is_duplicate, file_hash = is_duplicate_image(media_path)
                    if is_duplicate:
                        os.remove(media_path)
                        await message.channel.send(
                            f"Duplicate image detected! {attachment.filename} has already been uploaded.\n"
                            f"Hash: {file_hash[:16]}..."
                        )
                        continue

                    await message.channel.send(
                        f"Image {attachment.filename} saved to folder"
                    )

                    desc_name = (
                        os.path.splitext(os.path.basename(media_path))[0] + ".txt"
                    )
                    desc_path = os.path.join(desc_folder, desc_name)
                    with open(desc_path, "w") as desc:
                        desc.write(message.content if message.content else "")
                    await message.channel.send("Description saved to folder")

                    w1, h1, w2, h2 = resize(media_path)
                    await message.channel.send(
                        f"Resized image from {w1}x{h1} to {w2}x{h2}"
                    )

                    add_image_hash(attachment.filename, file_hash)
                    await message.channel.send(f"Hash saved: {file_hash[:16]}...")

                elif attachment.content_type.startswith("video/"):
                    media_path = os.path.join(media_folder, attachment.filename)
                    await attachment.save(media_path)

                    is_duplicate, file_hash = is_duplicate_image(media_path)
                    if is_duplicate:
                        os.remove(media_path)
                        await message.channel.send(
                            f"Duplicate video detected! {attachment.filename} has already been uploaded.\n"
                            f"Hash: {file_hash[:16]}..."
                        )
                        continue

                    await message.channel.send(
                        f"Video {attachment.filename} saved to folder"
                    )

                    desc_name = (
                        os.path.splitext(os.path.basename(media_path))[0] + ".txt"
                    )
                    desc_path = os.path.join(desc_folder, desc_name)
                    with open(desc_path, "w") as desc:
                        desc.write(message.content if message.content else "")
                    await message.channel.send("Description saved to folder")

                    add_image_hash(attachment.filename, file_hash)
                    await message.channel.send(f"Hash saved: {file_hash[:16]}...")


client.run(discord_token)
