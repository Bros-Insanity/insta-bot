# insta-bot
![GitHub](https://img.shields.io/badge/Version-0.4-purple) ![GitHub](https://img.shields.io/badge/License-MIT-blue) ![GitHub](https://img.shields.io/badge/Status-Unknown-orange) ![GitHub](https://img.shields.io/badge/Tests-Pending-orange)

Discord bot for sending images and their descriptions to the server, and posting one randomly each day on Instagram at a random time between 8 AM and 7 PM.

## Library Installation
`pip install -r requirements.txt`

## Usage
Upload an image to the Discord channel and write the desired description in the same message.
Every day at 7 AM, the bot selects an image and its associated description, as well as the time it will be posted (random time between 8 AM and 7 PM).
The bot posts only one image per day.

If the image exceeds the Instagram's maximum ratios ((4:5) or (1,91:1)), the image will be automatically padded with white pixels  to match the maximum ratio.

## Commands
- `!dump` : displays the remaining media and their total count
- `!dump_img` : displays the remaining images and their total count
- `!dump_vid` : displays the remaining videos and their total count
- `!dump_txt` : displays the remaining descriptions and their total count
- `!delete <image name>` : deletes the image and its description. ⚠️ the image name needs to be the name + the extension (e.g. `!delete image1.png`)
- `!delete_all` : deletes all images and descriptions

## Tests
- Commands : passing
- Scheduling : passing
- Discord interaction : passing
- Instagram posting (images) : passing
- Instagram posting (videos) : pending

Bot tested on a Debian 12 server

## Version changelog
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