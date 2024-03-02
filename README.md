# content-finder
## TODO
1. Refactoring
2. Blackjack
3. !history
4. Update !help
5. Add a way to only add channel's videos if certain keywords appear in title
6. Add args to commands (probably needs a new class for commands)
## Overview
A chatbot for Cytube focusing on YouTube, with an emphasis on avoiding the need for a YT API Key. Main functionality is to track YT channels and add new content to the specified Cytube channel.
## Requirements
- Docker & docker-compose - I've tightly coupled development with Docker in mind, if you want to run without you will need to fix a few things yourself for now (keep in mind you will **need** Python >= 3.10 and a postgres DB.)
- For Docker you **must** run: `docker volume create postgres_db` (or if on Linux change the docker-compose file to point to a directory on your host machine.)
## Setup
### Env vars
Set the environment variables in `docker-compose.yml`.  
`.env` file is no longer directly supported.

Run: `docker volume create postgres_db`
## docker-compose
### docker-compose.yml
### docker-compose.dev.yml
### docker-compose.format.yml

Included is `Dockerfile.format` which can be used to force format the entire codebase to conform to the above tools (except pylint! i.e. this Dockerfile will not lint the code.):
```
docker build -t content-finder-formatter -f Dockerfile.format .
docker run -v ${pwd}/cytubebot:/app/cytubebot --name content-finder-formatter content-finder-formatter
```
Alternatively use `docker-compose -f docker-compose.format.yml up`.