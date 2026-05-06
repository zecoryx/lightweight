#!/bin/bash
# LightWeight Installer (Linux/macOS)
set -e
echo "LightWeight is installing..."

OS="$(uname -s)"
ARCH="$(uname -m)"

# Match the published static assets under /dist.
case "$OS" in
    Darwin) OS_NAME="macos" ;;
    Linux) OS_NAME="linux" ;;
    *)
        echo "Unsupported operating system: $OS"
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64|amd64) ARCH_NAME="x86_64" ;;
    arm64|aarch64) ARCH_NAME="arm64" ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

BINARY_URL="https://lightweight.zecoryx.uz/dist/lightweight-${OS_NAME}-${ARCH_NAME}"

echo "Downloading LightWeight for $OS_NAME ($ARCH_NAME)..."
curl -L "$BINARY_URL" -o /tmp/lightweight
chmod +x /tmp/lightweight
sudo mv /tmp/lightweight /usr/local/bin/lightweight

echo "Done! Type 'lightweight chat' to start."
