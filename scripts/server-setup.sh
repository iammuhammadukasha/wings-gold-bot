#!/bin/bash
# One-time server setup — run in cPanel Terminal as upayztec
set -euo pipefail

mkdir -p ~/.ssh
chmod 700 ~/.ssh

DEPLOY_KEY="$HOME/.ssh/id_ed25519_wings_deploy"
DEPLOY_PUB="${DEPLOY_KEY}.pub"

if [ ! -f "$DEPLOY_KEY" ]; then
    echo "ERROR: Private deploy key not found at ${DEPLOY_KEY}"
    echo "Copy id_ed25519_wings_deploy from your PC into ~/.ssh/ on the server first."
    exit 1
fi

chmod 600 "$DEPLOY_KEY"
[ -f "$DEPLOY_PUB" ] && chmod 644 "$DEPLOY_PUB"

# GitHub host key
if ! grep -q "github.com" "$HOME/.ssh/known_hosts" 2>/dev/null; then
    ssh-keyscan -t ed25519 github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null
    chmod 644 "$HOME/.ssh/known_hosts"
fi

echo "Testing GitHub SSH..."
export GIT_SSH_COMMAND="ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes"
ssh -i "$DEPLOY_KEY" -o IdentitiesOnly=yes -T git@github.com || true

bash "$(dirname "$0")/deploy.sh"
echo "Server setup complete."
