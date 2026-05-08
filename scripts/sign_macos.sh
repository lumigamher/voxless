#!/usr/bin/env bash
#
# Sign dist/voxless.app with a stable self-signed identity ("voxless-dev").
#
# Why: macOS TCC (Accessibility / Input Monitoring / Microphone) tracks
# permissions by codesign authority + bundle id when the binary is NOT
# adhoc-signed. Adhoc signatures are keyed by cdhash, which changes on
# every build → every update wipes the user's permissions. A stable
# self-signed cert keeps permissions persistent across builds.
#
# Usage:
#   ./scripts/sign_macos.sh [path/to/voxless.app]
# Default path: ./dist/voxless.app
#
# This script is idempotent. It will create the dev cert in your login
# keychain on first run if it doesn't exist. The private key never
# leaves your machine and is NEVER committed.

set -euo pipefail

APP_PATH="${1:-dist/voxless.app}"
IDENTITY_NAME="voxless-dev"
KEYCHAIN="${HOME}/Library/Keychains/login.keychain-db"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

if [[ ! -d "$APP_PATH" ]]; then
  echo "error: app bundle not found at $APP_PATH" >&2
  exit 1
fi

if ! security find-certificate -c "$IDENTITY_NAME" "$KEYCHAIN" >/dev/null 2>&1; then
  echo "→ Creating self-signed code signing identity '$IDENTITY_NAME'..."
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$WORK_DIR/voxless.key" \
    -out "$WORK_DIR/voxless.crt" \
    -days 3650 -nodes \
    -subj "/CN=$IDENTITY_NAME" \
    -addext "extendedKeyUsage=codeSigning" \
    -addext "keyUsage=digitalSignature" \
    -addext "basicConstraints=critical,CA:false" \
    >/dev/null 2>&1

  openssl pkcs12 -export \
    -out "$WORK_DIR/voxless.p12" \
    -inkey "$WORK_DIR/voxless.key" \
    -in "$WORK_DIR/voxless.crt" \
    -passout pass:voxless \
    -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 \
    -name "$IDENTITY_NAME" >/dev/null

  security import "$WORK_DIR/voxless.p12" \
    -k "$KEYCHAIN" \
    -P voxless \
    -T /usr/bin/codesign \
    -A >/dev/null

  echo "→ Identity created. After approving Accessibility once, future"
  echo "  rebuilds keep your permission grant."
fi

echo "→ Stripping iCloud / quarantine xattrs..."
xattr -cr "$APP_PATH"

echo "→ Signing $APP_PATH..."
codesign --force --deep --sign "$IDENTITY_NAME" "$APP_PATH"

echo "→ Verifying..."
codesign --verify --deep "$APP_PATH"
codesign -dv "$APP_PATH" 2>&1 | grep -E "Authority|Identifier"

echo "✓ Done."
