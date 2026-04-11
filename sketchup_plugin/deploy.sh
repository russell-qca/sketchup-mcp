#!/bin/bash
# Deploy SketchUp MCP Plugin
# This script copies the plugin files to the SketchUp Plugins directory

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}SketchUp MCP Plugin Deployment${NC}"
echo "================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Source directory: $SCRIPT_DIR"

# Find SketchUp Plugins directory (macOS)
SKETCHUP_BASE="$HOME/Library/Application Support"
PLUGINS_DIR=""

# Try SketchUp 2025 first (preferred)
if [ -d "$SKETCHUP_BASE/SketchUp 2025/SketchUp/Plugins" ]; then
    PLUGINS_DIR="$SKETCHUP_BASE/SketchUp 2025/SketchUp/Plugins"
# Fallback: search for any SketchUp version
else
    for dir in "$SKETCHUP_BASE"/SketchUp*; do
        if [ -d "$dir/SketchUp/Plugins" ]; then
            PLUGINS_DIR="$dir/SketchUp/Plugins"
            break
        fi
    done
fi

if [ -z "$PLUGINS_DIR" ]; then
    echo -e "${RED}Error: Could not find SketchUp Plugins directory${NC}"
    echo "Expected location: ~/Library/Application Support/SketchUp 2026/SketchUp/Plugins/"
    exit 1
fi

echo "Target directory: $PLUGINS_DIR"
echo ""

# Check if SketchUp is running
if pgrep -x "SketchUp" > /dev/null; then
    echo -e "${RED}Warning: SketchUp is currently running!${NC}"
    echo "Please close SketchUp before deploying the plugin."
    read -p "Press Enter to continue anyway, or Ctrl+C to cancel..."
fi

echo "Deploying files..."

# Copy main plugin file
echo "  - Copying sketchup_mcp_server.rb"
cp "$SCRIPT_DIR/sketchup_mcp_server.rb" "$PLUGINS_DIR/"

# Create lib directory structure if it doesn't exist
echo "  - Creating lib/construction/ directory"
mkdir -p "$PLUGINS_DIR/lib/construction"

# Copy lib files
echo "  - Copying lib/construction.rb"
cp "$SCRIPT_DIR/lib/construction.rb" "$PLUGINS_DIR/lib/"

echo "  - Copying lib/construction/roof_truss.rb"
cp "$SCRIPT_DIR/lib/construction/roof_truss.rb" "$PLUGINS_DIR/lib/construction/"

echo "  - Copying lib/construction/wall.rb"
cp "$SCRIPT_DIR/lib/construction/wall.rb" "$PLUGINS_DIR/lib/construction/"

echo "  - Copying lib/construction/medeek_truss.rb"
cp "$SCRIPT_DIR/lib/construction/medeek_truss.rb" "$PLUGINS_DIR/lib/construction/"

echo "  - Copying lib/construction/medeek_foundation.rb"
cp "$SCRIPT_DIR/lib/construction/medeek_foundation.rb" "$PLUGINS_DIR/lib/construction/"

echo "  - Copying lib/construction/medeek_foundation_reader.rb"
cp "$SCRIPT_DIR/lib/construction/medeek_foundation_reader.rb" "$PLUGINS_DIR/lib/construction/"

echo "  - Copying lib/construction/medeek_wall.rb"
cp "$SCRIPT_DIR/lib/construction/medeek_wall.rb" "$PLUGINS_DIR/lib/construction/"

# Remove backup file if it exists in target
if [ -f "$PLUGINS_DIR/sketchup_mcp_server.rb.bak" ]; then
    echo "  - Removing old backup file"
    rm "$PLUGINS_DIR/sketchup_mcp_server.rb.bak"
fi

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Launch SketchUp"
echo "  2. Check the Ruby Console for 'CONSTRUCTION MODULES LOADED' message"
echo "  3. Test creating a truss through the MCP interface"
echo ""
