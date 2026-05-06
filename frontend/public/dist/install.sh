#!/bin/bash

# LightWeight One-liner Installer for Linux and macOS
# Usage: curl -fsSL https://lightweight.ai/install.sh | sh

set -e

echo "🪶 LightWeight o'rnatilmoqda..."

# OS va Arxitekturani aniqlash
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Darwin) OS_NAME="macos" ;;
    Linux) OS_NAME="linux" ;;
    *)
        echo "Qo'llab-quvvatlanmaydigan operatsion tizim: $OS"
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64|amd64) ARCH_NAME="x86_64" ;;
    arm64|aarch64) ARCH_NAME="arm64" ;;
    *)
        echo "Qo'llab-quvvatlanmaydigan arxitektura: $ARCH"
        exit 1
        ;;
esac

BINARY_URL="https://lightweight.zecoryx.uz/dist/lightweight-${OS_NAME}-${ARCH_NAME}"

# Binary faylni yuklab olish
echo "Eng so'nggi versiya yuklab olinmoqda: $OS_NAME $ARCH_NAME..."
curl -L "$BINARY_URL" -o /tmp/lightweight

# Dasturni tizimga o'rnatish
echo "Tizimga joylashtirilmoqda..."
chmod +x /tmp/lightweight
sudo mv /tmp/lightweight /usr/local/bin/lightweight

echo "LightWeight muvaffaqiyatli o'rnatildi!"
echo "Siz endi 'lightweight chat' buyrug'ini ishlatishingiz mumkin."
