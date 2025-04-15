# insta-bot
![GitHub](https://img.shields.io/badge/Version-0.3.1-purple) ![GitHub](https://img.shields.io/badge/License-MIT-blue) ![GitHub](https://img.shields.io/badge/Status-Broken-red) ![GitHub](https://img.shields.io/badge/Tests-Failing-red)

Discord bot for sending images and their descriptions to the server, and posting one randomly each day on Instagram at a random time between 8 AM and 7 PM.

## Library Installation
`pip install -r requirements.txt`

## Usage
Upload an image to the Discord channel and write the desired description in the same message.
Every day at 7 AM, the bot selects an image and its associated description, as well as the time it will be posted (random time between 8 AM and 7 PM).
The bot posts only one image per day.

If the image exceeds the Instagram's maximum ratios ((4:5) or (1,91:1)), the image will be automatically padded with white pixels  to match the maximum ratio.

## Commands
- `dump` : displays the remaining images and their total count
- `!dump_txt` : displays the remaining descriptions and their total count
- `!delete <image name>` : deletes the image and its description. ⚠️ the image name needs to be the name + the extension (e.g. `!delete image1.png`)
- `!delete_all` : deletes all images and descriptions

## Tests
- Commands : passing
- Scheduling : failing
- Discord interaction : passing
- Instagram posting : passing

Bot tested on a Debian 12 server

## Version changelog
- Added image name display when image is sent
- Added message sent by the bot in the channel when Instagram login failed