# insta-bot
![GitHub](https://img.shields.io/badge/Version-0.5-purple) ![GitHub](https://img.shields.io/badge/License-MIT-blue) ![GitHub](https://img.shields.io/badge/Status-Unknown-orange) ![GitHub](https://img.shields.io/badge/Tests-Pending-orange)

Discord bot for sending images and their descriptions to the server, and posting one randomly each day on Instagram at a random time between 8 AM and 7 PM.

## Library Installation
`pip install -r requirements.txt`

## Configuration
Create a `.env` file in the root directory with the following variables:
```env
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_target_channel_id
AUTO_SYNC_ON_STARTUP=true # Set to false to disable automatic Instagram sync on startup
```

## Usage
Upload an image or video to the Discord channel and write the desired description in the same message. You can also use the `/upload` slash command.
Every day, the bot selects an image and its associated description, and schedules it to be posted at a random time between 8 AM and 7 PM.
The bot posts only one media per day.

If an image exceeds Instagram's maximum ratios (4:5 or 1.91:1), it will be automatically padded with white pixels to match the maximum ratio.

**Duplicate Prevention:** The bot now features a robust duplicate detection system using perceptual hashing (pHash) for images and SHA256 for videos. It prevents you from uploading the same file twice to the queue and can sync with your past Instagram posts to ensure old content isn't reposted.

## Commands (Slash Commands)
- `/dump` : Lists all media files (images and videos) in the queue and their total count.
- `/dump_img` : Lists the remaining images in the queue and their total count.
- `/dump_vid` : Lists the remaining videos in the queue and their total count.
- `/dump_txt` : Lists all description files and their total count.
- `/delete <filename>` : Deletes a specific media file and its description. ⚠️ The filename must include the extension (e.g., `/delete image1.png`).
- `/delete_all` : Deletes all queued media, descriptions, and clears the hash database.
- `/upload <media> <description>` : Uploads an image or video with its caption to the queue.
- `/next_post` : Shows the exact scheduled date and time for the next Instagram post.
- `/sync_instagram` : Manually triggers a background sync of all previously posted Instagram media to update the anti-duplicate database.
- `/hash_stats` : Displays statistics about the stored media hashes (Instagram posts vs. local files).
- `/sync_commands` : Forces a re-sync of Discord slash commands if they are not appearing.

## Tests
- Commands : passing
- Scheduling : passing
- Discord interaction : passing
- Instagram posting (images) : passing
- Instagram posting (videos) : pending
- Duplicate Detection (Hashing) : passing

Bot tested on an Alpine server.

## Version changelog
### 0.5.1
- Video upload bug fix
- scheduler bug fix

### 0.5
- Migrated all bot commands to Discord Slash Commands (`/`).
- Implemented robust duplicate detection using perceptual hash for images and SHA256 for videos.
- Added Instagram account syncing to build a database of past posts and prevent re-uploads.
- Added new slash commands: `/upload`, `/next_post`, `/sync_instagram`, `/hash_stats`, and `/sync_commands`.
- Added `AUTO_SYNC_ON_STARTUP` environment variable for automated database building.
- Bot still handles attachments sent normally (without commands) by hashing and saving them automatically.

### 0.4
- Added video support
- Added `!dump_video` command
- Moved `!dump` command to `!dump_img` command
- `!dump` command now displays both images and videos remaining
- Corrected scheduling issue

### 0.3.1
- Added image name display when image is sent
- Added message sent by the bot in the channel when Instagram login failed

### 0.3
- Added image resize to instagram's Aspect Ratio
- Added `!delete_all` command

### 0.2
- Added `!dump_txt` command

### 0.1
- Bot setup
