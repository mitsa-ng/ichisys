#!/bin/bash
set -e

echo "=== Building Ichiban Kuji Desktop App ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Build frontend
echo ""
echo "--- Step 1: Build frontend ---"
cd "$ROOT_DIR/frontend"
npm run build

# 2. Install Python deps
echo ""
echo "--- Step 2: Install Python deps ---"
cd "$ROOT_DIR/backend"
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
pip install -q pyinstaller

# 3. PyInstaller backend
echo ""
echo "--- Step 3: Package backend with PyInstaller ---"
cd "$ROOT_DIR/backend"
pyinstaller ichiban-server.spec --clean --noconfirm

# 4. Copy frontend dist into PyInstaller output
echo ""
echo "--- Step 4: Bundle frontend with backend ---"
mkdir -p "$ROOT_DIR/backend/dist/ichiban-server/frontend"
cp -r "$ROOT_DIR/frontend/dist" "$ROOT_DIR/backend/dist/ichiban-server/frontend/"

echo "Backend package ready at: $ROOT_DIR/backend/dist/ichiban-server/"

# 5. Build Electron app
echo ""
echo "--- Step 5: Build Electron app ---"
cd "$ROOT_DIR/electron"
npm install --silent
npm run build:all

echo ""
echo "=== Build complete ==="
echo "Output: $ROOT_DIR/electron/dist/"
ls -la "$ROOT_DIR/electron/dist/"
