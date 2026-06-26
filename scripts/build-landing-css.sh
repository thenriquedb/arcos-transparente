#!/bin/sh
# Gera ui/static/tailwind.css a partir dos templates/JS da landing usando o
# binario standalone do Tailwind (sem Node). Rode apos mudar classes em
# ui/templates/*.html ou ui/static/*.js. O CSS gerado e versionado (o binario nao).
#
# Uso: sh scripts/build-landing-css.sh
set -eu

VERSION="v3.4.16"
CACHE_DIR=".cache"
BIN="$CACHE_DIR/tailwindcss"

# Detecta plataforma para baixar o binario correto.
os="$(uname -s)"
arch="$(uname -m)"
case "$os-$arch" in
  Darwin-arm64) asset="tailwindcss-macos-arm64" ;;
  Darwin-x86_64) asset="tailwindcss-macos-x64" ;;
  Linux-x86_64) asset="tailwindcss-linux-x64" ;;
  Linux-aarch64) asset="tailwindcss-linux-arm64" ;;
  *) echo "Plataforma nao suportada: $os-$arch" >&2; exit 1 ;;
esac

mkdir -p "$CACHE_DIR"
if [ ! -x "$BIN" ]; then
  url="https://github.com/tailwindlabs/tailwindcss/releases/download/$VERSION/$asset"
  echo "Baixando Tailwind standalone ($asset $VERSION)..."
  curl -fsSL "$url" -o "$BIN"
  chmod +x "$BIN"
fi

"$BIN" -c tailwind.config.js -i ui/static/tailwind.input.css -o ui/static/tailwind.css --minify
echo "Gerado ui/static/tailwind.css"
