#!/bin/bash
# One-time bootstrap for cPanel Terminal — run as upayztec
set -euo pipefail

REPO_DIR="/home/upayztec/wings-gold-bot"
REPO_URL="git@github.com:iammuhammadukasha/wings-gold-bot.git"
BRANCH="master"
DEPLOY_KEY="$HOME/.ssh/id_ed25519_wings_deploy"
DEPLOY_PUB="${DEPLOY_KEY}.pub"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ ! -f "$DEPLOY_KEY" ]; then
    ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -C "wings-gold-bot-server-deploy"
fi
chmod 600 "$DEPLOY_KEY"
chmod 644 "$DEPLOY_PUB"

if ! grep -q "github.com" "$HOME/.ssh/known_hosts" 2>/dev/null; then
    ssh-keyscan -t ed25519 github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null
    chmod 644 "$HOME/.ssh/known_hosts"
fi

echo ""
echo "=========================================="
echo "ADD THIS DEPLOY KEY TO GITHUB"
echo "Repo: iammuhammadukasha/wings-gold-bot"
echo "Settings -> Deploy keys -> Add deploy key"
echo "Title: wings-gold-bot-server"
echo "Allow write access: OFF"
echo "=========================================="
cat "$DEPLOY_PUB"
echo "=========================================="
echo ""

export GIT_SSH_COMMAND="ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

AUTH_MSG="$(ssh -i "$DEPLOY_KEY" -o IdentitiesOnly=yes -T git@github.com 2>&1 || true)"
if [[ "$AUTH_MSG" != *"successfully authenticated"* ]]; then
    echo "GitHub auth not ready yet."
    echo "Message was: $AUTH_MSG"
    echo "Add the deploy key above to GitHub, then re-run:"
    echo "  curl -fsSL https://raw.githubusercontent.com/iammuhammadukasha/wings-gold-bot/master/scripts/cpanel-bootstrap.sh | bash"
    exit 0
fi

if [ ! -d "$REPO_DIR/.git" ]; then
    if [ -d "$REPO_DIR" ] && [ "$(ls -A "$REPO_DIR" 2>/dev/null)" ]; then
        echo "Backing up live config/state..."
        [ -f "$REPO_DIR/config.py" ] && cp "$REPO_DIR/config.py" /tmp/wings_config.py.bak
        [ -d "$REPO_DIR/state" ] && cp -r "$REPO_DIR/state" /tmp/wings_state.bak
        mv "$REPO_DIR" "${REPO_DIR}.bak.$(date +%Y%m%d%H%M%S)"
    fi
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    [ -f /tmp/wings_config.py.bak ] && cp /tmp/wings_config.py.bak "$REPO_DIR/config.py"
    [ -d /tmp/wings_state.bak ] && cp -r /tmp/wings_state.bak/* "$REPO_DIR/state/" 2>/dev/null || mkdir -p "$REPO_DIR/state"
else
    bash "$REPO_DIR/scripts/deploy.sh"
fi

echo "Bootstrap complete."
cd "$REPO_DIR"
git log -1 --oneline
ls -la scripts/
