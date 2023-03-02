#!/bin/sh

set -e  # exit on any error

# check tools
command -v poetry >/dev/null || (printf "\e[0;31mpoetry not installed!\e[0m"; exit 1)

# check environment
[ -d .venv ] || (printf "\e[0;31mpython virtual environment is not set up!\e[0m"; exit 1)

# .env file is mandatory
[ -f .env ] || (printf "\e[0;31m.env file not found!\e[0m" && exit 1)

VERSION=$(git branch --show-current)
sed -i "s%BOT_VERSION=.*%BOT_VERSION=$VERSION%" .env

# check if .env file is up to date
while read -r line
do
   grep -q "^${line%%=*}" .env || (printf "\e[0;31m$line\e[0m - param not defined in .env!\n"; exit 1)
done <<< $(sed 's/^#.*//' env.example | sed '/^[[:space:]]*$/d')

poetry run python ./src/main.py
