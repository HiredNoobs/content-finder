# content-finder

## Overview
A chatbot for Cytube focusing on YouTube, with an emphasis on avoiding the need for a YT API Key. Main functionality is to track YT channels and add new content to the specified Cytube channel.

## Requirements
- Docker & docker compose v2 - I've tightly coupled development with Docker in mind, if you want to run without you will need to fix a few things yourself for now (keep in mind you will **need** Python >= 3.10 and a postgres DB.)
- If running on Windows, you **must** run: `docker volume create postgres_db`

## Usage
Simply run ``docker compose up``. The compose file is expecting a number of environment variables to either be in you environmnet or in a ``.env`` file at the top level directory.

## Redis
The ``redis`` directory contains a helper script ``redis.py`` for pushing and pulling data manually into Redis - mainly for backing up and seeding new data if messing with the volume.

Usage:

```bash
python3 redis.py push FILENAME
python3 redis.py pull
```
