# SketchUp MCP Server

Connect Claude to SketchUp via the Model Context Protocol (MCP).

## Architecture

```
Claude Desktop (MCP client)
        ↕  stdio (MCP protocol)
sketchup-mcp  (Python MCP server)
        ↕  HTTP REST  localhost:8080
sketchup_mcp_server.rb  (Ruby WEBrick plugin inside SketchUp)
        ↕  SketchUp Ruby API
 SketchUp Model
```

---

## Installation

### Part 1 — Install the SketchUp Ruby Plugin

#### Automatic Installation (Recommended)

The plugin now has a modular structure. Use the deployment script:

```bash
cd sketchup-mcp/sketchup_plugin
./deploy.sh
```

The script will:
- Find your SketchUp Plugins directory automatically
- Copy all necessary files (main plugin + lib/ modules)
- Create the required directory structure
- Warn if SketchUp is running

#### Manual Installation

If you prefer manual installation:

**Plugins folder location:**

| OS      | Path |
|---------|------|
| macOS   | `~/Library/Application Support/SketchUp <version>/SketchUp/Plugins/` |
| Windows | `%APPDATA%\SketchUp\SketchUp <version>\SketchUp\Plugins\` |

**Copy these files:**
```bash
PLUGINS="~/Library/Application Support/SketchUp 2024/SketchUp/Plugins"

cp sketchup_plugin/sketchup_mcp_server.rb "$PLUGINS/"
mkdir -p "$PLUGINS/lib/construction"
cp sketchup_plugin/lib/construction.rb "$PLUGINS/lib/"
cp sketchup_plugin/lib/construction/roof_truss.rb "$PLUGINS/lib/construction/"
```

#### Start the Server

Restart SketchUp. The server **auto-starts on port 8080** when SketchUp loads.

You can also use:
- **Plugins → MCP Server → Start Server**
- **Plugins → MCP Server → Stop Server**
- **Plugins → MCP Server → Restart Server**

#### Verify

Open the SketchUp Ruby Console. You should see these startup messages:
```
====== LOADING SKETCHUP MCP PLUGIN ======
====== REQUIRES COMPLETE ======
====== CONSTRUCTION MODULES LOADED ======
====== SKETCHUP MCP SERVER STARTED ======
```

Test the connection:
```ruby
require 'net/http'
Net::HTTP.get(URI('http://localhost:8080/model/info'))
```

You should see a JSON response with your model's details.

---

### Part 2 — Install the Python MCP Server

#### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

#### Install with uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone or navigate to this repository
cd sketchup-mcp

# Install the package and dependencies
uv pip install -e .

# The CLI command 'sketchup-mcp' is now available
```

#### Install with pip

```bash
cd sketchup-mcp
pip install -e .
```

#### Test it standalone

```bash
# With SketchUp running and plugin loaded:
sketchup-mcp
```

The server will start and communicate via stdio. Press Ctrl+C to stop.

---

### Part 3 — Connect to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "sketchup": {
      "command": "sketchup-mcp"
    }
  }
}
```

**Note:** If you installed without `-e` or want to use an absolute path:

```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/sketchup-mcp", "sketchup-mcp"]
    }
  }
}
```

Restart Claude Desktop. You should see a SketchUp icon in the tools panel.

---

## MCP Resources (Construction Knowledge)

Claude can automatically reference these construction guides when needed:

| Resource | Description |
|----------|-------------|
| `construction://roof-trusses` | Comprehensive roof truss design guide: types (king post, fink, queen post), dimensions, code requirements, SketchUp best practices |
| `construction://framing` | Standard framing practices: wall/floor framing, lumber sizes, spacing, headers, openings, and SketchUp modeling |
| `construction://stairs` | Stair design standards: building codes, 2R+T formula, calculations, stair types, and SketchUp implementation |

## Available MCP Tools

### Query tools
| Tool | Description |
|------|-------------|
| `get_model_info` | Model name, path, unit, entity/layer/material counts |
| `list_layers` | All layers with visibility |
| `list_materials` | All materials with color/texture |
| `list_entities` | Faces, edges, groups, instances (optionally inside a group) |
| `list_components` | All component definitions |

### Basic geometry
| Tool | Description |
|------|-------------|
| `create_face` | Polygon from ordered `[x,y,z]` points |
| `create_edge` | Line segment between two points |
| `create_group` | Empty named group |
| `create_box` | Rectangular prism (width × depth × height) |

### Advanced geometry
| Tool | Description |
|------|-------------|
| `create_circle` | Circle with radius, center, normal, segments |
| `create_arc` | Arc with start/end angles, radius |
| `create_polygon` | Regular polygon (triangle, pentagon, hexagon, etc.) |
| `push_pull` | Push/pull a face by distance |
| `follow_me` | Extrude a face along a path (array of edge IDs) |

### Transformations
| Tool | Description |
|------|-------------|
| `move_entity` | Move entity by [x, y, z] vector |
| `rotate_entity` | Rotate entity around axis by angle (degrees) |
| `scale_entity` | Scale entity (uniform or [x, y, z]) |

### Components
| Tool | Description |
|------|-------------|
| `create_component` | New component definition + first instance |
| `place_component` | Place existing definition at a point |

### Construction (High-Level)
| Tool | Description |
|------|-------------|
| `create_roof_truss` | Create engineered roof trusses: king post, fink (W-truss), or queen post with proper geometry and dimensions |

### Execute Ruby
| Tool | Description |
|------|-------------|
| `execute_ruby` | Run arbitrary Ruby code inside SketchUp; returns result + stdout |

---

## Example Claude prompts

### Basic Operations
```
"Show me all the layers in my SketchUp model"

"Create a 10×10×3 foot box at the origin on layer 'Walls'"

"Create a circle with radius 12 inches at the origin"

"Create a hexagon with radius 6 inches, then push-pull it 2 inches"

"List every face in the model and tell me which ones are larger than 50 sq inches"

"Create a component called 'Chair' and place three copies at (0,0,0), (60,0,0), and (120,0,0)"

"Move entity 12345 by vector [10, 0, 5]"

"Rotate entity 67890 around the Z-axis by 45 degrees"
```

### Construction (With Knowledge Resources)
```
"Create roof trusses for a 24-foot span building with a 6:12 pitch"

"I need fink trusses for a 30-foot wide building, spaced 24 inches on center, covering a 40-foot length"

"Create a king post truss for my 20-foot garage with an 8:12 pitch"

"Frame a building that's 24 feet × 30 feet with 8-foot walls and add roof trusses"

"What type of roof truss should I use for a 28-foot span? Then create them."

"Add queen post roof trusses to my building with proper spacing"
```

**Note**: Claude will automatically reference the construction knowledge resources (roof trusses, framing standards, stairs) when relevant to provide accurate, code-compliant designs.

---

## Development

### Project Structure

```
sketchup-mcp/
├── src/
│   └── sketchup_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       └── server.py              # Main MCP server code
├── sketchup_plugin/
│   ├── sketchup_mcp_server.rb     # Main Ruby HTTP server
│   ├── deploy.sh                  # Deployment script
│   ├── DEPLOYMENT.md              # Deployment documentation
│   └── lib/                       # Modular construction features
│       ├── construction.rb        # Module loader
│       └── construction/
│           └── roof_truss.rb      # Roof truss implementation
├── resources/                     # MCP construction knowledge
│   ├── roof_trusses.md            # Used by Claude
│   ├── framing_standards.md       # Used by Claude
│   ├── stairs.md                  # Used by Claude
│   ├── fink_truss_engineering_spec.md      # Developer docs
│   └── truss_implementation_guide.md       # Developer docs
├── tests/                         # Test suite (TODO)
├── pyproject.toml                 # Package configuration
└── README.md
```

### Install for development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests (once implemented)
pytest

# Run the server directly
python -m sketchup_mcp
```

### Adding New Construction Features

The plugin uses a modular architecture for scalability:

1. **Create new module**: `sketchup_plugin/lib/construction/feature_name.rb`
2. **Define class**: `module Construction; class FeatureName; def self.create(params); end; end; end`
3. **Register module**: Add `require_relative 'construction/feature_name'` to `lib/construction.rb`
4. **Add handler**: In main server, add `def self.handle_create_feature(params); Construction::FeatureName.create(params); end`
5. **Add route**: Add to `ROUTES` hash
6. **Add MCP tool**: Register in Python `server.py`
7. **Deploy**: Run `./deploy.sh`

This keeps the main server file clean and each feature isolated. See `lib/construction/roof_truss.rb` for a complete example.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot connect to SketchUp" | Make sure SketchUp is open and the plugin is loaded |
| `command not found: sketchup-mcp` | Run `uv pip install -e .` or add `~/.local/bin` to PATH |
| **Port 8080 in use** | **Kill processes using port:** `lsof -i :8080 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9`<br>Or edit `PORT = 8080` in `.rb` file and `SKETCHUP_BASE_URL` in `server.py` |
| Plugin not loading | Check SketchUp's Ruby Console for errors after `load` |
| WEBrick error (Ruby 3.2+) | Use the updated plugin version (uses TCPServer instead of WEBrick) |
| Units seem wrong | SketchUp's default unit is **inches**; adjust coordinates accordingly |

---

## Security note

The `execute_ruby` tool runs arbitrary code inside SketchUp. Only use it
with prompts you trust, and consider disabling the route in the `.rb` file
if you don't need it.

---

## License

MIT
