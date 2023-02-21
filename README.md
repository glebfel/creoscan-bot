TBP Creoscan
================
Telegram bot for parsing media data from popular social networks


## Installation

### local
* `poetry install`
* `docker-compose up -d db redis`
* `./start.sh` - will tell which ENV vars are mandatory and should be provided in `.env` file

### containers
* fill `.env` file with mandatory fields (see `docker-compose.yaml`)
* `docker-compose up -d`

### deployment
* provided `git-hook-post-receive` will do neccessary stuff to deploy Bot on push
