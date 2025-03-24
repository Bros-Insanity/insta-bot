# insta-bot
![GitHub](https://img.shields.io/badge/Version-0.2-purple) ![GitHub](https://img.shields.io/badge/License-MIT-blue) ![GitHub](https://img.shields.io/badge/Status-Broken-red) ![GitHub](https://img.shields.io/badge/Tests-Failing-red)

Discord bot for sending images and their descriptions to the server, and posting one randomly each day on Instagram at a random time between 8 AM and 7 PM.
## Library Installation
`pip install -r requirements.txt`

## Usage
Upload an image to the Discord channel and write the desired description in the same message.
The image will be automatically padded with white pixels to make it square.
Every day at 7 AM, the bot selects an image and its associated description, as well as the time it will be posted (random time between 8 AM and 7 PM).
The bot posts only one image per day.

## Commands
- `dump` : displays the remaining images and their total count
- `!dump_txt` : displays the remaining descriptions and their total count
- `!delete <image name>` : deletes the image and its description. ⚠️ the image name needs to be the name + the extension (e.g. `!delete image1.png`)
## Tests
- Commands : passing
- Scheduling : failing
- Discord interaction : passing
- Instagram posting : passing

Bot tested on a Debian 12 server