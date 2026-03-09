# SketchUp MCP Plugin Deployment

## Quick Deploy

To update the plugin in SketchUp:

```bash
cd /Users/manhattan/PycharmProjects/sketchup-mcp/sketchup_plugin
./deploy.sh
```

## What Gets Deployed

The deployment script copies:
- `sketchup_mcp_server.rb` → Main plugin file
- `lib/construction.rb` → Construction module loader
- `lib/construction/roof_truss.rb` → Roof truss implementation

**Target location**: `~/Library/Application Support/SketchUp <version>/SketchUp/Plugins/`

## Manual Deployment

If you prefer to deploy manually:

1. Close SketchUp if it's running
2. Copy files to the SketchUp Plugins directory:
   ```bash
   PLUGINS="$HOME/Library/Application Support/SketchUp 2024/SketchUp/Plugins"

   cp sketchup_mcp_server.rb "$PLUGINS/"
   mkdir -p "$PLUGINS/lib/construction"
   cp lib/construction.rb "$PLUGINS/lib/"
   cp lib/construction/roof_truss.rb "$PLUGINS/lib/construction/"
   ```
3. Launch SketchUp

## Verification

After deployment:
1. Open SketchUp
2. Open Ruby Console (Window → Ruby Console)
3. Look for these messages:
   - `====== LOADING SKETCHUP MCP PLUGIN ======`
   - `====== REQUIRES COMPLETE ======`
   - `====== CONSTRUCTION MODULES LOADED ======`
   - `====== SKETCHUP MCP SERVER STARTED ======`

4. Test creating a truss via the MCP interface

## File Structure

After deployment, the Plugins folder should contain:

```
Plugins/
├── sketchup_mcp_server.rb
└── lib/
    ├── construction.rb
    └── construction/
        └── roof_truss.rb
```

## Adding New Construction Features

To add a new construction feature (e.g., stairs, decks):

1. Create new file: `lib/construction/feature_name.rb`
2. Define class: `Construction::FeatureName`
3. Add `require_relative 'construction/feature_name'` to `lib/construction.rb`
4. Add handler method to main server: `handle_create_feature`
5. Run `./deploy.sh` to update plugin
