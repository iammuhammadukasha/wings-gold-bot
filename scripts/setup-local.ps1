# Switch local repo to GitHub SSH after adding the public key to GitHub.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

git remote set-url origin git@github.com:iammuhammadukasha/wings-gold-bot.git
Write-Host "Remote set to SSH. Testing GitHub..."
ssh -T git@github.com
git remote -v
