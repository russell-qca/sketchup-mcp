#!/usr/bin/env python3
"""
SketchUp MCP Server
Bridges Claude (MCP protocol over stdio) to a running SketchUp instance
via the WEBrick HTTP server embedded in the SketchUp Ruby plugin.
"""

import asyncio
import json
import sys
import logging
from typing import Any
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKETCHUP_BASE_URL = "http://localhost:8080"
HTTP_TIMEOUT = 10.0

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
log = logging.getLogger("sketchup-mcp")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def su_get(path: str, params: dict | None = None) -> dict:
    """Send a GET request to the SketchUp Ruby server."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            r = await client.get(f"{SKETCHUP_BASE_URL}{path}", params=params or {})
            r.raise_for_status()
            data = r.json()
            # Check if the response contains an error field
            if isinstance(data, dict) and "error" in data:
                raise RuntimeError(f"SketchUp error: {data['error']}")
            return data
        except httpx.ConnectError:
            raise RuntimeError(
                "Cannot connect to SketchUp. Make sure SketchUp is running "
                "and the MCP plugin is loaded (Plugins → MCP Server → Start Server)."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Request to SketchUp timed out after {HTTP_TIMEOUT}s. "
                "The operation may be taking too long or SketchUp may be unresponsive."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"SketchUp server returned error {e.response.status_code}: {e.response.text}"
            )
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON response from SketchUp: {e}")


async def su_post(path: str, body: dict | None = None) -> dict:
    """Send a POST request to the SketchUp Ruby server."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            r = await client.post(
                f"{SKETCHUP_BASE_URL}{path}",
                json=body or {},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
            # Check if the response contains an error field
            if isinstance(data, dict) and "error" in data:
                raise RuntimeError(f"SketchUp error: {data['error']}")
            return data
        except httpx.ConnectError:
            raise RuntimeError(
                "Cannot connect to SketchUp. Make sure SketchUp is running "
                "and the MCP plugin is loaded (Plugins → MCP Server → Start Server)."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Request to SketchUp timed out after {HTTP_TIMEOUT}s. "
                "The operation may be taking too long or SketchUp may be unresponsive."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"SketchUp server returned error {e.response.status_code}: {e.response.text}"
            )
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON response from SketchUp: {e}")


def ok(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, indent=2))]


def err(message: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"Error: {message}")]

# ---------------------------------------------------------------------------
# MCP Server definition
# ---------------------------------------------------------------------------

app = Server("sketchup-mcp")

# Resource directory
RESOURCES_DIR = Path(__file__).parent.parent.parent / "resources"

# ---------------------------------------------------------------------------
# Resources - Construction Knowledge Base
# ---------------------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """Provide construction knowledge resources to Claude."""
    return [
        types.Resource(
            uri="construction://roof-trusses",
            name="Roof Truss Design Guide",
            mimeType="text/markdown",
            description="Comprehensive guide for roof truss design including types (king post, fink, queen post), dimensions, code requirements, and SketchUp modeling best practices"
        ),
        types.Resource(
            uri="construction://framing",
            name="Framing Standards",
            mimeType="text/markdown",
            description="Standard framing practices for walls, floors, headers, and openings including lumber sizes, spacing, and SketchUp modeling guidelines"
        ),
        types.Resource(
            uri="construction://stairs",
            name="Stair Design Standards",
            mimeType="text/markdown",
            description="Building code requirements, design formulas (2R+T rule), stair types, and calculation methods for residential and commercial stairs"
        ),
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read construction knowledge resource files."""
    resource_map = {
        "construction://roof-trusses": RESOURCES_DIR / "roof_trusses.md",
        "construction://framing": RESOURCES_DIR / "framing_standards.md",
        "construction://stairs": RESOURCES_DIR / "stairs.md",
    }

    resource_file = resource_map.get(uri)
    if not resource_file:
        raise ValueError(f"Unknown resource: {uri}")

    if not resource_file.exists():
        raise FileNotFoundError(f"Resource file not found: {resource_file}")

    return resource_file.read_text()

# ---------------------------------------------------------------------------
# Tool list
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [

        # ── Query tools ────────────────────────────────────────────────────

        types.Tool(
            name="get_model_info",
            description=(
                "Get general information about the currently open SketchUp model: "
                "name, file path, unit system, entity/layer/material counts."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        types.Tool(
            name="list_layers",
            description="List all layers (tags) in the SketchUp model with their visibility.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        types.Tool(
            name="list_materials",
            description="List all materials in the SketchUp model with their colors and textures.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        types.Tool(
            name="list_entities",
            description=(
                "List entities (faces, edges, groups, component instances) in the model "
                "or inside a named group."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "If provided, list entities inside this group. "
                                       "Otherwise lists top-level model entities.",
                    }
                },
                "required": [],
            },
        ),

        types.Tool(
            name="list_components",
            description="List all component definitions in the SketchUp model.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Create geometry ────────────────────────────────────────────────

        types.Tool(
            name="create_face",
            description=(
                "Create a flat face (polygon) in SketchUp from an ordered list of 3D points. "
                "Points are in SketchUp's default unit (inches unless model is metric)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "description": "Ordered list of [x, y, z] vertices. Minimum 3.",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "minItems": 3,
                    },
                    "layer": {"type": "string", "description": "Layer name to assign (created if missing)."},
                    "material": {"type": "string", "description": "Material name to assign (created if missing)."},
                },
                "required": ["points"],
            },
        ),

        types.Tool(
            name="create_edge",
            description="Create a line segment (edge) between two 3D points.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] start point",
                    },
                    "end": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] end point",
                    },
                    "layer": {"type": "string"},
                },
                "required": ["start", "end"],
            },
        ),

        types.Tool(
            name="create_group",
            description="Create an empty named group in SketchUp, optionally on a layer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":  {"type": "string", "description": "Name for the new group"},
                    "layer": {"type": "string", "description": "Layer to place the group on"},
                },
                "required": [],
            },
        ),

        types.Tool(
            name="create_box",
            description=(
                "Create a 3-D box (rectangular prism) by specifying width, depth, height. "
                "Optionally provide an origin [x, y, z] for the base corner."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "width":    {"type": "number", "description": "Size along X axis"},
                    "depth":    {"type": "number", "description": "Size along Y axis"},
                    "height":   {"type": "number", "description": "Size along Z axis"},
                    "origin":   {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] base corner (default [0,0,0])",
                    },
                    "layer":    {"type": "string"},
                    "material": {"type": "string"},
                },
                "required": ["width", "depth", "height"],
            },
        ),

        # ── Advanced geometry ──────────────────────────────────────────────

        types.Tool(
            name="create_circle",
            description=(
                "Create a circle in SketchUp from a center point, normal vector, and radius. "
                "Returns edges forming the circle."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] center point (default [0,0,0])",
                    },
                    "normal": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] normal vector (default [0,0,1] for Z-axis)",
                    },
                    "radius": {"type": "number", "description": "Circle radius (must be positive)"},
                    "segments": {"type": "integer", "description": "Number of segments (default 24, min 3)"},
                    "layer": {"type": "string"},
                    "material": {"type": "string"},
                },
                "required": ["radius"],
            },
        ),

        types.Tool(
            name="create_arc",
            description=(
                "Create an arc in SketchUp. Specify center, radius, start/end angles in degrees."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] center point",
                    },
                    "xaxis": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] X-axis vector (default [1,0,0])",
                    },
                    "normal": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] normal vector",
                    },
                    "radius": {"type": "number", "description": "Arc radius"},
                    "start_angle": {"type": "number", "description": "Start angle in degrees (default 0)"},
                    "end_angle": {"type": "number", "description": "End angle in degrees (default 180)"},
                    "segments": {"type": "integer", "description": "Number of segments (default 12)"},
                    "layer": {"type": "string"},
                    "material": {"type": "string"},
                },
                "required": ["radius"],
            },
        ),

        types.Tool(
            name="create_polygon",
            description=(
                "Create a regular polygon (triangle, pentagon, hexagon, etc.) with n sides."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] center point",
                    },
                    "normal": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] normal vector",
                    },
                    "radius": {"type": "number", "description": "Radius from center to vertices"},
                    "num_sides": {"type": "integer", "description": "Number of sides (min 3)"},
                    "inscribed": {"type": "boolean", "description": "True if inscribed (default), false if circumscribed"},
                    "layer": {"type": "string"},
                    "material": {"type": "string"},
                },
                "required": ["radius", "num_sides"],
            },
        ),

        types.Tool(
            name="push_pull",
            description=(
                "Push/pull a face by a specified distance. Positive distance extrudes outward, "
                "negative pulls inward."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "integer", "description": "ID of the face to push/pull"},
                    "distance": {"type": "number", "description": "Distance to push (positive) or pull (negative)"},
                },
                "required": ["entity_id", "distance"],
            },
        ),

        types.Tool(
            name="follow_me",
            description=(
                "Extrude a face along a path (array of edge IDs). This is SketchUp's Follow Me tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "face_id": {"type": "integer", "description": "ID of the face to extrude"},
                    "path_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Array of edge IDs forming the path",
                    },
                },
                "required": ["face_id", "path_ids"],
            },
        ),

        # ── Transformations ────────────────────────────────────────────────

        types.Tool(
            name="move_entity",
            description="Move (translate) an entity by a vector [x, y, z].",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "integer", "description": "ID of the entity to move"},
                    "vector": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] translation vector",
                    },
                },
                "required": ["entity_id", "vector"],
            },
        ),

        types.Tool(
            name="rotate_entity",
            description="Rotate an entity around an axis by a given angle in degrees.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "integer", "description": "ID of the entity to rotate"},
                    "axis_point": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] point on the rotation axis",
                    },
                    "axis_vector": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] direction vector of rotation axis",
                    },
                    "angle": {"type": "number", "description": "Rotation angle in degrees"},
                },
                "required": ["entity_id", "axis_point", "axis_vector", "angle"],
            },
        ),

        types.Tool(
            name="scale_entity",
            description=(
                "Scale an entity. Provide a single number for uniform scaling, "
                "or [x, y, z] array for non-uniform scaling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "integer", "description": "ID of the entity to scale"},
                    "scale": {
                        "description": "Scale factor (number) or [x, y, z] scale factors (array)",
                        "oneOf": [
                            {"type": "number"},
                            {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                        ],
                    },
                    "origin": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] origin point for scaling (default [0,0,0])",
                    },
                },
                "required": ["entity_id", "scale"],
            },
        ),

        # ── Components ─────────────────────────────────────────────────────

        types.Tool(
            name="create_component",
            description=(
                "Create a new (empty) component definition and place one instance in the model. "
                "Returns the definition name and instance ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name":        {"type": "string", "description": "Component definition name"},
                    "description": {"type": "string"},
                    "origin":      {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Where to place the instance",
                    },
                },
                "required": ["name"],
            },
        ),

        types.Tool(
            name="place_component",
            description=(
                "Place an instance of an existing component definition into the model at a given origin."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name":   {"type": "string", "description": "Exact name of the component definition"},
                    "origin": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "required": ["name"],
            },
        ),

        # ── Construction ───────────────────────────────────────────────────

        types.Tool(
            name="create_roof_truss",
            description=(
                "Create engineered roof trusses with accurate geometry based on professional truss analysis. "
                "Supports king post (simple, up to 26') and fink/W-truss (most common, 20-60'). "
                "Trusses include proper web patterns, angled members, and realistic connections. "
                "Use construction://roof-trusses resource for detailed guidance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "span": {
                        "type": "number",
                        "description": "Clear span in feet (wall-to-wall distance, excluding overhang)"
                    },
                    "pitch": {
                        "type": "string",
                        "description": "Roof pitch as 'rise:run' (e.g., '6:12', '8:12'). Common: 6:12",
                        "default": "6:12"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["king", "fink"],
                        "description": "Truss type: king (simple with center post) or fink (W-pattern, most common)",
                        "default": "fink"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of trusses to create",
                        "default": 1
                    },
                    "spacing": {
                        "type": "number",
                        "description": "Spacing between trusses in inches (typically 24 OC)",
                        "default": 24.0
                    },
                    "overhang": {
                        "type": "number",
                        "description": "Overhang beyond walls in inches (each side). Standard: 12-24 inches",
                        "default": 12.0
                    },
                    "lumber_size": {
                        "type": "string",
                        "enum": ["2x4", "2x6", "2x8"],
                        "description": "Lumber size for members (actual dimensions: 2x4=1.5×3.5, 2x6=1.5×5.5)",
                        "default": "2x4"
                    },
                    "origin": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Left wall bottom position [x, y, z] in inches"
                    },
                    "layer": {
                        "type": "string",
                        "description": "Layer name for trusses"
                    }
                },
                "required": ["span"]
            },
        ),

        # ── Execute Ruby ───────────────────────────────────────────────────

        types.Tool(
            name="execute_ruby",
            description=(
                "Execute arbitrary Ruby code inside SketchUp. "
                "The code runs in the context of the SU_MCP module and has full access "
                "to the SketchUp Ruby API (Sketchup, Geom, UI, etc.). "
                "Returns the result of the last expression and any puts/print output. "
                "Use with care — this can modify or delete model data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Ruby source code to execute",
                    }
                },
                "required": ["code"],
            },
        ),
    ]

# ---------------------------------------------------------------------------
# Tool call handler
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        # ── Query ──────────────────────────────────────────────────────────
        if name == "get_model_info":
            return ok(await su_get("/model/info"))

        elif name == "list_layers":
            return ok(await su_get("/model/layers"))

        elif name == "list_materials":
            return ok(await su_get("/model/materials"))

        elif name == "list_entities":
            params = {}
            if "group_name" in arguments:
                params["group_name"] = arguments["group_name"]
            return ok(await su_get("/model/entities", params))

        elif name == "list_components":
            return ok(await su_get("/model/components"))

        # ── Create geometry ────────────────────────────────────────────────
        elif name == "create_face":
            return ok(await su_post("/geometry/face", arguments))

        elif name == "create_edge":
            return ok(await su_post("/geometry/edge", arguments))

        elif name == "create_group":
            return ok(await su_post("/geometry/group", arguments))

        elif name == "create_box":
            return ok(await su_post("/geometry/box", arguments))

        # ── Advanced geometry ──────────────────────────────────────────
        elif name == "create_circle":
            return ok(await su_post("/geometry/circle", arguments))

        elif name == "create_arc":
            return ok(await su_post("/geometry/arc", arguments))

        elif name == "create_polygon":
            return ok(await su_post("/geometry/polygon", arguments))

        elif name == "push_pull":
            return ok(await su_post("/geometry/pushpull", arguments))

        elif name == "follow_me":
            return ok(await su_post("/geometry/followme", arguments))

        # ── Transformations ────────────────────────────────────────────
        elif name == "move_entity":
            return ok(await su_post("/transform/move", arguments))

        elif name == "rotate_entity":
            return ok(await su_post("/transform/rotate", arguments))

        elif name == "scale_entity":
            return ok(await su_post("/transform/scale", arguments))

        # ── Components ─────────────────────────────────────────────────────
        elif name == "create_component":
            return ok(await su_post("/components/create", arguments))

        elif name == "place_component":
            return ok(await su_post("/components/place", arguments))

        # ── Construction ───────────────────────────────────────────────────
        elif name == "create_roof_truss":
            return ok(await su_post("/construction/roof_truss", arguments))

        # ── Execute Ruby ───────────────────────────────────────────────────
        elif name == "execute_ruby":
            result = await su_post("/ruby/execute", arguments)
            if "error" in result:
                return err(f"Ruby error: {result['error']}\n" +
                           "\n".join(result.get("backtrace", [])))
            return ok(result)

        else:
            return err(f"Unknown tool: {name}")

    except RuntimeError as exc:
        return err(str(exc))
    except Exception as exc:
        log.exception("Unexpected error in tool %s", name)
        return err(f"Unexpected error: {exc}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
