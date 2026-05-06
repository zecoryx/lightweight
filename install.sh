#!/bin/bash

# LightWeight One-liner Installer for Linux and macOS
# Usage: curl -fsSL https://lightweight.ai/install.sh | sh

set -e

echo "🚀 LightWeight o'rnatilmoqda..."

# OS va Arxitekturani aniqlash
OS="$(uname -s)"
ARCH="$(uname -m)"

BINARY_URL="https://lightweight.zecoryx.uz/dist/lightweight-${OS,,}-${ARCH}"

# Binary faylni yuklab olish
echo "📥 Eng so'nggi versiya yuklab olinmoqda: $OS $ARCH..."
curl -L "$BINARY_URL" -o /tmp/lightweight

# Dasturni tizimga o'rnatish
echo "⚙️ Tizimga joylashtirilmoqda..."
chmod +x /tmp/lightweight
sudo mv /tmp/lightweight /usr/local/bin/lightweight

echo "✅ LightWeight muvaffaqiyatli o'rnatildi!"
echo "Siz endi 'lightweight chat' buyrug'ini ishlatishingiz mumkin."
