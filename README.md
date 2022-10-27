# content-finder
## TODO
1. Proper DB AKA Postgres
2. Add/remove channels from chat
4. Blackjack
## Overview
A simple chat bot for Cytube, goes through channels added to `channel-ids.txt` and adds new videos to cytube.

Start with: `docker-compose up --abort-on-container-exit` or `docker-compose up -d`
If you start with `-d`, running !kill in chat will not kill the DB container - you will need to manually handle this, but !kill is still recommended.
## Requirements
- Docker & docker-compose - I've tightly coupled development with Docker in mind, if you want to run without you will need to fix a few things yourself for now (keep in mind you will **need** Python >= 3.10 and a postgres DB )
## Setup
### Env vars
Set the environment variables in `docker-compose.yml`.
`.env` file is no longer directly supported.

Run: `docker volume create postgres_db`
### Channels
Add channel ids and channel names to `channel-ids.txt`, e.g.:
```
# channel name 1
channel_id_1
# channel name 2
channel_id_2
```
## Extra tools
The main `Dockerfile` runs tox (pytests, black, flask8, pylint, and isort - in that order) to encourage decent code quality. This does increase build times significantly so you may wish to avoid making extremely small iterative changes or use set the `docker-compose.yml` to use `Dockerfile.no-checks` - before pushing changes run with the regular dockerfile at least once.

Included is `Dockerfile.format` which can be used to force format the entire codebase to conform to the above tools (except pylint! This Dockerfile will not lint the code.):
```
docker build -t content-finder-formatter -f Dockerfile.format .
docker run -v ${pwd}/cytubebot:/app/cytubebot --name content-finder-formatter content-finder-formatter
```