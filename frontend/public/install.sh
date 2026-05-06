#!/bin/bash
# LightWeight Installer (Linux/macOS)
set -e
echo "🚀 LightWeight is installing..."

OS="$(uname -s)"
ARCH="$(uname -m)"

# GitHub Release manzili
# Eslatma: GitHub-da Release yaratganingizda fayl nomlarini quyidagicha qiling:
# lightweight-linux, lightweight-macos
if [ "$OS" = "Darwin" ]; then
    BINARY_NAME="lightweight-macos"
else
    BINARY_NAME="lightweight-linux"
fi

BINARY_URL="https://github.com/zecoryx/lightweight/releases/latest/download/${BINARY_NAME}"

echo "📥 Downloading from GitHub..."
curl -L "$BINARY_URL" -o /tmp/lightweight
chmod +x /tmp/lightweight
sudo mv /tmp/lightweight /usr/local/bin/lightweight

echo "✅ Done! Type 'lightweight chat' to start."
