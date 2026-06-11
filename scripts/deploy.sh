#!/bin/bash
# Run on server: pull latest code from GitHub into /home/upayztec/wings-gold-bot
set -euo pipefail

REPO_DIR="/home/upayztec/wings-gold-bot"
REPO_URL="git@github.com:iammuhammadukasha/wings-gold-bot.git"
BRANCH="master"
SSH_KEY="$HOME/.ssh/id_ed25519_wings_deploy"

export GIT_SSH_COMMAND="ssh -i ${SSH_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Cloning repo into ${REPO_DIR}..."
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
else
    echo "Pulling latest ${BRANCH}..."
    cd "$REPO_DIR"
    if [ -f config.py ]; then
        cp config.py /tmp/wings_config.py.bak
    fi
    git fetch origin "$BRANCH"
    git reset --hard "origin/${BRANCH}"
    if [ -f /tmp/wings_config.py.bak ]; then
        cp /tmp/wings_config.py.bak config.py
        rm /tmp/wings_config.py.bak
    fi
fi

echo "Deploy complete:"
cd "$REPO_DIR"
git log -1 --oneline
