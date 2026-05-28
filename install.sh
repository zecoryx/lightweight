#!/bin/bash

# LightWeight One-liner Installer for Linux and macOS
# Usage: curl -fsSL https://lightweight.zecoryx.uz/install.sh | sh

set -euo pipefail

echo "LightWeight o'rnatilmoqda..."

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

case "${OS_NAME}-${ARCH_NAME}" in
    linux-x86_64|macos-arm64) ;;
    *)
        echo "Bu platforma uchun binary hali chiqarilmagan: ${OS_NAME}-${ARCH_NAME}"
        echo "Hozir mavjud binarylar: linux-x86_64, macos-arm64, windows-x86_64.exe"
        exit 1
        ;;
esac

BINARY_URL="https://lightweight.zecoryx.uz/dist/lightweight-${OS_NAME}-${ARCH_NAME}"
CHECKSUM_URL="${BINARY_URL}.sha256"
TMP_BIN="$(mktemp /tmp/lightweight.XXXXXX)"
trap 'rm -f "$TMP_BIN" "$TMP_BIN.sha256"' EXIT

# Binary faylni yuklab olish
echo "Eng so'nggi versiya yuklab olinmoqda: $OS_NAME $ARCH_NAME..."
curl -fL "$BINARY_URL" -o "$TMP_BIN"

if curl -fsL "$CHECKSUM_URL" -o "$TMP_BIN.sha256"; then
    echo "Checksum tekshirilmoqda..."
    EXPECTED="$(awk '{print $1}' "$TMP_BIN.sha256")"
    ACTUAL="$(sha256sum "$TMP_BIN" | awk '{print $1}')"
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "Checksum mos kelmadi. O'rnatish to'xtatildi."
        exit 1
    fi
else
    echo "Ogohlantirish: checksum fayli topilmadi, tekshiruv o'tkazilmadi."
fi

# Dasturni tizimga o'rnatish
echo "Tizimga joylashtirilmoqda..."
chmod +x "$TMP_BIN"
sudo mv "$TMP_BIN" /usr/local/bin/lightweight
trap - EXIT

echo "LightWeight muvaffaqiyatli o'rnatildi!"
echo "Avval tekshiring: lightweight doctor"
echo "Modeldan oldin reja ko'ring: lightweight check qwen:32b --mode fit"
