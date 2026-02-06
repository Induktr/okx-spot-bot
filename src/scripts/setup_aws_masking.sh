#!/bin/bash

# A.S.T.R.A. v1.5 - AWS MASKING TOOL (Cloudflare WARP)
# This script installs Cloudflare WARP to mask AWS EC2 IP addresses.

echo "🚀 Starting AWS IP Masking Setup (Cloudflare WARP)..."

# 1. Add Cloudflare GPG key and repo
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

# 2. Install WARP
sudo apt-get update && sudo apt-get install cloudflare-warp -y

# 3. Register and Connect (Headless Mode)
echo "🔑 Registering WARP client..."
warp-cli --accept-tos registration new
warp-cli --accept-tos mode proxy
warp-cli --accept-tos connect

# 4. Verify IP
echo "🌐 Verifying your new masked IP..."
ORIGINAL_IP=$(curl -s https://ifconfig.me)
sleep 5
NEW_IP=$(curl -s --proxy socks5://127.0.0.1:40000 https://ifconfig.me)

echo "------------------------------------------------"
echo "✅ SETUP COMPLETE!"
echo "Original AWS IP: $ORIGINAL_IP"
echo "New Masked IP (via SOCKS5): $NEW_IP"
echo "------------------------------------------------"
echo "📍 TO USE IN BOT: Set TIKTOK_PROXY=socks5://127.0.0.1:40000 in your .env"
echo "------------------------------------------------"
