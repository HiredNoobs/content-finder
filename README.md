# content-finder
## Overview
A simple chat bot for Cytube, goes through channels added to `channel-ids.txt` and adds new videos to cytube.
## Requirements
- Docker - can be run without but recommended.
- Python 3.10 - if desparate not to install 3.10 for some reason then goto `cytubebot/chatbot/chat_bot` line ~113 and swap switch case for if-elif-else.
## Setup
### Env fie
Make `.env` with `CYTUBE_URL`, `CYTUBE_URL_CHANNEL_NAME`, `CYTUBE_USERNAME`, and `CYTUBE_PASSWORD`.

<<<<<<< HEAD
# Setup
## Env fie
Make `.env` with `CYTUBE_URL`, `CYTUBE_URL_CHANNEL_NAME`, `CYTUBE_USERNAME`, and `CYTUBE_PASSWORD`.

Something like:
=======
Example:
>>>>>>> 80cf8075065cdab6ce3579d3b86cce2a8ba4f0f1
```
CYTUBE_URL=https://cytu.be/
CYTUBE_URL_CHANNEL_NAME=my_channel
CYTUBE_USERNAME=my_username
CYTUBE_PASSWORD=my_password
```
### Channels
Add channel ids and channel names to `channel-ids.txt`, e.g.:
```
# channel name 1
channel_id_1
# channel name 2
channel_id_2
```
## Running
I strongly stopping the bot with `!kill` in chat since this will handle closing all resources properly, but killing the containers/scripts outright is usually fine so long as the DB isn't being written to at the time.
### Docker compose
Start: `docker-compose up -d`  
Stop: `docker-compose down`
### No docker
You **MUST** edit `DB_FILE` in `cytubebot/contentfinder/conf.ini` file correctly or everything will explode - I would recommend a full path but for relative, it must be relative to `cytube/contentfinder/database.py` (untested but `../../content.db` should work.)

<<<<<<< HEAD
# Running
## Docker compose
`docker-compose up`
## No docker
Assuming bash shell:
```
python -m virtualenv venv
source venv/Scripts/activate
pip install -r requirements.txt
python main.py
```
=======
Assuming bash shell on linux (for bash on windows `source venv/Scripts/activate`):
```
python -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt  OR  pip install -e .
python cytubebot/main.py
```
Use `-r requirements.txt` for dev environment (assuming your IDE can resolve the paths properly) else use `pip install -e .`
>>>>>>> 80cf8075065cdab6ce3579d3b86cce2a8ba4f0f1
