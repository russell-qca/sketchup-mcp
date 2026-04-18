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
            uri="construction://foundations",
            name="Foundation Creation Guide - Medeek Foundation Plugin",
            mimeType="text/markdown",
            description="CRITICAL GUIDE for using the Medeek Foundation Plugin API. Explains the correct workflow (create with defaults, then modify), common mistakes to avoid, and how to use create_foundation tool properly. READ THIS BEFORE creating any foundations."
        ),
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
        "construction://foundations": RESOURCES_DIR / "foundation_guide.md",
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
                "Create BASIC roof trusses using Medeek Truss Plugin. This creates trusses with DEFAULT settings (pitch, type, geometry only).\n\n"
                "**IMPORTANT: This tool ONLY creates the basic truss structure. To add advanced features (sheathing, fascia, cladding, etc.), use the 'modify_truss' tool AFTER creation.**\n\n"
                "Supports 14 truss types: king, queen, fink, howe, fan, mod_queen, double_fink, double_howe, "
                "mod_fan, triple_fink, triple_howe, quad_fink, quad_howe, penta_howe.\n\n"
                "**WORKFLOW for trusses with features:**\n"
                "1. Call create_roof_truss (creates basic trusses)\n"
                "2. Call modify_truss with advanced options (adds sheathing, fascia, etc.)\n\n"
                "**GABLE WALL ORIENTATION:**\n"
                "The top_plate_corners must be ordered so that the FIRST and THIRD edges define the GABLE walls (short walls, non-bearing), and the SECOND and FOURTH edges define the BEARING walls (long walls where trusses sit).\n\n"
                "**CRITICAL RULES:**\n"
                "1. NEVER create test geometry. Query existing model data BEFORE creating.\n"
                "2. After calling this tool, use execute_ruby to audit for stray groups and clean up.\n"
                "3. If layer parameter provided, assign the group to that layer after creation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "span": {
                        "type": "number",
                        "description": "Clear span in feet (wall-to-wall distance, excluding overhang). Default: 24 feet"
                    },
                    "pitch": {
                        "type": "string",
                        "description": "Roof pitch as 'rise:run' (e.g., '6:12', '8:12'). Common: 6:12",
                        "default": "6:12"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["king", "queen", "fink", "howe", "fan", "mod_queen", "double_fink", "double_howe", "mod_fan", "triple_fink", "triple_howe", "quad_fink", "quad_howe", "penta_howe"],
                        "description": "Truss type. Common types: fink (W-pattern, most common), king (simple with center post), howe (M-pattern), queen (two center posts)",
                        "default": "fink"
                    },
                    "building_depth": {
                        "type": "number",
                        "description": "Building depth in feet (perpendicular to span). Medeek will fill this area with trusses at proper spacing. Default: 24 feet. Ignored if top_plate_corners provided."
                    },
                    "spacing": {
                        "type": "number",
                        "description": "Spacing between trusses in inches (typically 24 OC). Only used by Medeek to determine truss placement.",
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
                        "description": "Left wall bottom position [x, y, z] in inches. Ignored if top_plate_corners provided."
                    },
                    "top_plate_corners": {
                        "type": "array",
                        "description": (
                            "Provide the 4 outer corner points from the top of the top plate face. Format: [[x1,y1,z1], [x2,y2,z2], [x3,y3,z3], [x4,y4,z4]].\n\n"
                            "CRITICAL — Gable wall rule: The FIRST edge (points 1→2) defines the FRONT GABLE wall, and the THIRD edge (points 3→4) defines the BACK GABLE wall. These are the short, non-bearing walls. The SECOND edge (points 2→3) and FOURTH edge (points 4→1) are the BEARING walls (long walls where truss heels sit). Trusses span between the bearing walls and repeat along the gable walls.\n\n"
                            "To determine which points go where:\n"
                            "1. Identify the GABLE walls (short walls, non-bearing). These are perpendicular to the truss span.\n"
                            "2. Identify the BEARING walls (long walls where trusses sit). The span is the distance between these walls.\n"
                            "3. Point 1 = left corner of front gable wall. Point 2 = right corner of front gable wall.\n"
                            "4. Point 3 = right corner of back gable wall (opposite point 2). Point 4 = left corner of back gable wall (opposite point 1).\n"
                            "5. The truss span is the distance from point 1 to point 4 (or point 2 to point 3).\n"
                            "6. Trusses repeat along the distance from point 1 to point 2 (or point 4 to point 3).\n\n"
                            "Example — 40'×60' building, trusses bear on the 60' long walls, span across the 40' dimension:\n"
                            "- Span = 40' (480\"). Trusses repeat along the 60' (720\") dimension.\n"
                            "- Front gable wall (40' wide) at Y=0, running X=0 to X=480.\n"
                            "- Back gable wall (40' wide) at Y=720, running X=0 to X=480.\n"
                            "- Left bearing wall (60' long) at X=0, running Y=0 to Y=720.\n"
                            "- Right bearing wall (60' long) at X=480, running Y=0 to Y=720.\n"
                            "- Correct corners: [[0,0,z], [480,0,z], [480,720,z], [0,720,z]]\n"
                            "- First edge (0,0 → 480,0) = 40' front gable wall ✓\n"
                            "- Second edge (480,0 → 480,720) = 60' right bearing wall ✓\n"
                            "- Third edge (480,720 → 0,720) = 40' back gable wall ✓\n"
                            "- Fourth edge (0,720 → 0,0) = 60' left bearing wall ✓\n\n"
                            "Common mistake to avoid: Do NOT order the corners so that the first edge runs along a bearing wall. The first and third edges must be the gable walls (short walls)."
                        ),
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3
                        },
                        "minItems": 4,
                        "maxItems": 4
                    },
                    "layer": {
                        "type": "string",
                        "description": "Layer name for trusses"
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="create_wall",
            description=(
                "Create a framed wall with studs, plates, and optional openings (doors/windows). "
                "Automatically places studs at proper spacing (16\" or 24\" OC), adds double top plates, "
                "and creates proper framing around openings with kings, jacks, headers, and cripples."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "length": {
                        "type": "number",
                        "description": "Wall length in feet"
                    },
                    "height": {
                        "type": "number",
                        "description": "Wall height in feet (default: 8)",
                        "default": 8.0
                    },
                    "stud_spacing": {
                        "type": "number",
                        "description": "Stud spacing in inches on-center (typically 16 or 24)",
                        "default": 16.0
                    },
                    "lumber_size": {
                        "type": "string",
                        "enum": ["2x4", "2x6", "2x8"],
                        "description": "Lumber size for framing members",
                        "default": "2x4"
                    },
                    "openings": {
                        "type": "array",
                        "description": "Array of door/window openings",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["door", "window"],
                                    "description": "Opening type"
                                },
                                "position": {
                                    "type": "number",
                                    "description": "Center position along wall in feet (from left end)"
                                },
                                "width": {
                                    "type": "number",
                                    "description": "Opening width in feet"
                                },
                                "height": {
                                    "type": "number",
                                    "description": "Opening height in feet"
                                }
                            },
                            "required": ["type", "position", "width", "height"]
                        }
                    },
                    "origin": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Left end position [x, y, z] in inches"
                    },
                    "layer": {
                        "type": "string",
                        "description": "Layer name for wall"
                    }
                },
                "required": ["length"]
            },
        ),

        types.Tool(
            name="create_foundation",
            description=(
                "Create concrete slab-on-grade foundation (slab, footer, footing) using Medeek Foundation Plugin. "
                "**USE THIS TOOL for any request involving: concrete slabs, footers, footings, foundations, slab-on-grade, or concrete pads.** "
                "**DO NOT use execute_ruby or other geometry tools to create slabs/foundations - ALWAYS use this tool instead.** "
                "\n\n"
                "**IMPORTANT: Read the construction://foundations resource BEFORE using this tool for the first time.**"
                "\n\n"
                "**How this tool works (Medeek API workflow):**\n"
                "1. Creates slab-on-grade with DEFAULT settings using only the outline geometry\n"
                "2. Automatically modifies ALL requested parameters (depth, thickness, rebar, bolts, etc.) using sog_set_attribute with regen=false\n"
                "3. Sets the final parameter with regen=true to regenerate once with all custom settings applied\n"
                "\n"
                "**You only need to call this tool ONCE** - it handles the complete create-then-modify workflow automatically. "
                "Do NOT call this tool multiple times. Do NOT try to create then modify separately. This tool does everything in ONE call."
                "\n\n"
                "Requires Medeek Foundation Plugin to be installed and licensed. "
                "Creates professional foundation with footing (footer), concrete slab, optional garage curb, optional rebar reinforcement, and optional anchor bolts. "
                "Supports top/bottom footing bars, slab reinforcement (welded wire fabric), anchor bolts with sill plate configuration. "
                "\n\n"
                "**CRITICAL: This tool returns 'slab_top_z' in the response** - the authoritative Z position of the top of slab surface. "
                "**ALWAYS use this slab_top_z value when placing walls, framing, or any geometry on top of the foundation.** "
                "Do NOT assume Z=0, do NOT calculate offsets - use the returned slab_top_z value directly for accurate wall placement."
                "\n\n"
                "Common use cases: 'create a 40x60 slab', 'concrete slab with footer', 'foundation with rebar', 'slab-on-grade foundation'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "outline_points": {
                        "type": "array",
                        "description": "Array of corner points [[x1,y1,z1], [x2,y2,z2], ...] defining the foundation perimeter. Points should be in order (clockwise or counter-clockwise). Minimum 3 points.",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3
                        },
                        "minItems": 3
                    },
                    "foundation_depth": {
                        "type": "number",
                        "description": "Total foundation depth in inches (from top of slab to bottom of footing). Default: 24 inches",
                        "default": 24.0
                    },
                    "slab_thickness": {
                        "type": "number",
                        "description": "Concrete slab thickness in inches. Default: 4 inches",
                        "default": 4.0
                    },
                    "footing_width": {
                        "type": "number",
                        "description": "Footing width in inches. Default: 16 inches",
                        "default": 16.0
                    },
                    "garage_curb": {
                        "type": "boolean",
                        "description": "Create garage door curb. Default: false",
                        "default": False
                    },
                    "curb_width": {
                        "type": "number",
                        "description": "Garage curb width in inches (only used if garage_curb is true). Default: 4 inches",
                        "default": 4.0
                    },
                    "curb_height": {
                        "type": "number",
                        "description": "Garage curb height in inches (only used if garage_curb is true). Default: 4 inches",
                        "default": 4.0
                    },
                    "rebar_enabled": {
                        "type": "boolean",
                        "description": "Enable rebar/reinforcement options. Default: false",
                        "default": False
                    },
                    "top_bar_enabled": {
                        "type": "boolean",
                        "description": "Enable top footing bars (only if rebar_enabled is true). Default: false",
                        "default": False
                    },
                    "top_bar_diameter": {
                        "type": "number",
                        "description": "Top bar diameter in inches (e.g., 0.5 for #4 rebar, 0.625 for #5). Default: 0.5",
                        "default": 0.5
                    },
                    "top_bar_quantity": {
                        "type": "integer",
                        "description": "Number of top bars. Default: 2",
                        "default": 2
                    },
                    "bottom_bar_enabled": {
                        "type": "boolean",
                        "description": "Enable bottom footing bars (only if rebar_enabled is true). Default: false",
                        "default": False
                    },
                    "bottom_bar_diameter": {
                        "type": "number",
                        "description": "Bottom bar diameter in inches. Default: 0.5",
                        "default": 0.5
                    },
                    "bottom_bar_quantity": {
                        "type": "integer",
                        "description": "Number of bottom bars. Default: 2",
                        "default": 2
                    },
                    "slab_reinforcement_enabled": {
                        "type": "boolean",
                        "description": "Enable slab reinforcement (only if rebar_enabled is true). Default: false",
                        "default": False
                    },
                    "slab_reinforcement_type": {
                        "type": "string",
                        "description": "Slab reinforcement type (e.g., 'WWF' for welded wire fabric). Default: WWF",
                        "default": "WWF"
                    },
                    "slab_reinforcement_spacing": {
                        "type": "number",
                        "description": "Slab reinforcement spacing in inches. Default: 12",
                        "default": 12.0
                    },
                    "anchor_bolts_enabled": {
                        "type": "boolean",
                        "description": "Enable anchor bolts and sill plate. Default: false",
                        "default": False
                    },
                    "bolt_size": {
                        "type": "string",
                        "description": "Anchor bolt length in inches (e.g., '10', '12', '14'). Default: '12'",
                        "default": "12"
                    },
                    "bolt_diameter": {
                        "type": "string",
                        "description": "Anchor bolt diameter (e.g., '1/2', '5/8'). Default: '1/2'",
                        "default": "1/2"
                    },
                    "washer_type": {
                        "type": "string",
                        "description": "Washer size (e.g., '2x2', '3x3'). Default: '2x2'",
                        "default": "2x2"
                    },
                    "bolt_spacing_ft": {
                        "type": "number",
                        "description": "Anchor bolt spacing in feet on center. Typical: 6 feet. Default: 6.0",
                        "default": 6.0
                    },
                    "sill_width": {
                        "type": "number",
                        "description": "Sill plate width in inches (e.g., 3.5 for 2x4 actual). Default: 3.5",
                        "default": 3.5
                    },
                    "sill_thickness": {
                        "type": "number",
                        "description": "Sill plate thickness in inches (e.g., 1.5 for 2x4 actual). Default: 1.5",
                        "default": 1.5
                    },
                    "corner_distance": {
                        "type": "number",
                        "description": "Distance from corner for first anchor bolt in inches. Default: 12",
                        "default": 12.0
                    },
                    "fpsf_enabled": {
                        "type": "boolean",
                        "description": "Enable Frost Protected Shallow Foundation (FPSF) insulation. Default: false",
                        "default": False
                    },
                    "insulation_type": {
                        "type": "string",
                        "description": "FPSF insulation type: 'Vertical Only', 'Vert. and Horz.', or 'None'. Default: 'None'",
                        "default": "None"
                    },
                    "vertical_insulation": {
                        "type": "number",
                        "description": "Vertical insulation R-value. Default: 2.0",
                        "default": 2.0
                    },
                    "wing_insulation": {
                        "type": "number",
                        "description": "Horizontal wing insulation R-value. Default: 2.0",
                        "default": 2.0
                    },
                    "corner_insulation": {
                        "type": "number",
                        "description": "Corner insulation R-value. Default: 2.0",
                        "default": 2.0
                    },
                    "dim_a": {
                        "type": "number",
                        "description": "FPSF dimension A in inches. Default: 24.0",
                        "default": 24.0
                    },
                    "dim_b": {
                        "type": "number",
                        "description": "FPSF dimension B in inches. Default: 24.0",
                        "default": 24.0
                    },
                    "dim_c": {
                        "type": "number",
                        "description": "FPSF dimension C in inches. Default: 24.0",
                        "default": 24.0
                    },
                    "slab_insulation_enabled": {
                        "type": "boolean",
                        "description": "Enable slab insulation. Default: false",
                        "default": False
                    },
                    "slab_insulation": {
                        "type": "number",
                        "description": "Slab insulation R-value. Default: 2.0",
                        "default": 2.0
                    },
                    "subbase_enabled": {
                        "type": "boolean",
                        "description": "Enable subbase layer beneath slab. Default: false",
                        "default": False
                    },
                    "subbase_depth": {
                        "type": "number",
                        "description": "Subbase depth in inches. Default: 4.0",
                        "default": 4.0
                    },
                    "subbase_material": {
                        "type": "string",
                        "description": "Subbase material: 'Gravel', 'Stone1', or 'corrugated_metal'. Default: 'Gravel'",
                        "default": "Gravel"
                    },
                    "drain_enabled": {
                        "type": "boolean",
                        "description": "Enable perimeter drain. Default: false",
                        "default": False
                    },
                    "layer": {
                        "type": "string",
                        "description": "Layer name for foundation"
                    }
                },
                "required": ["outline_points"]
            },
        ),

        types.Tool(
            name="read_foundation_attributes",
            description=(
                "Read all attributes from an existing Medeek Foundation assembly. "
                "Returns all foundation parameters including dimensions, rebar settings, anchor bolts, etc. "
                "Can read from a selected foundation or by providing the group name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Foundation group name (optional). If not provided, will read from currently selected foundation."
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="read_foundation_attribute",
            description=(
                "Read a specific attribute from an existing Medeek Foundation assembly. "
                "Use this to query individual parameters like BOLTSIZE, FDEPTH, SLABTHICKNESS, etc. "
                "See Medeek Foundation API documentation for available attribute names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "The attribute name to read (e.g., 'BOLTSIZE', 'FDEPTH', 'SLABTHICKNESS', 'FTGWIDTH')"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Foundation group name (optional). If not provided, will read from currently selected foundation."
                    }
                },
                "required": ["attribute_name"]
            },
        ),

        types.Tool(
            name="get_foundation_info",
            description=(
                "Get foundation information from an existing slab-on-grade foundation in the model. "
                "**CRITICAL: USE THIS TOOL to query the exact slab_top_z value before placing walls on a foundation.** "
                "\n\n"
                "This tool reads the foundation from the model and returns the authoritative slab_top_z value "
                "that should be used for wall placement. Do NOT assume the slab starts at Z=0 or guess the "
                "slab thickness - always query the foundation first.\n\n"
                "Returns: slab_top_z (the Z coordinate of the top of the concrete slab where walls sit), "
                "outline_points (with Z coordinates set to slab_top_z for easy wall placement), "
                "and other foundation parameters.\n\n"
                "**WORKFLOW FOR PLACING WALLS ON FOUNDATION:**\n"
                "1. Call get_foundation_info to get slab_top_z\n"
                "2. Use the returned slab_top_z for all wall Z coordinates\n"
                "3. Use outline_points for wall perimeter placement (already at correct Z)\n\n"
                "If no group_name provided, will find the first foundation in the model."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Foundation group name (optional). If not provided, will find any foundation in the model."
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="modify_foundation",
            description=(
                "Modify an EXISTING slab-on-grade foundation created by Medeek Foundation Plugin. "
                "**USE THIS TOOL to change parameters on an existing foundation** instead of deleting and recreating. "
                "\n\n"
                "**IMPORTANT: This modifies an existing foundation - do NOT use create_foundation to modify!**"
                "\n\n"
                "How this works:\n"
                "1. Takes the foundation group_name (from create_foundation response or read_foundation_attributes)\n"
                "2. Accepts any parameters you want to change (depth, thickness, rebar, bolts, etc.)\n"
                "3. Uses Medeek API to modify the existing foundation with sog_set_attribute\n"
                "4. Regenerates the foundation once with all changes applied\n"
                "\n"
                "**Common use cases:**\n"
                "- Change foundation depth from 24\" to 30\"\n"
                "- Add rebar to existing foundation\n"
                "- Add or remove anchor bolts\n"
                "- Modify garage curb settings\n"
                "- Change slab thickness or footing width\n"
                "\n"
                "**You only need to provide the parameters you want to CHANGE** - unchanged parameters remain as-is."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Foundation group name (e.g., 'FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308'). Get this from create_foundation response or read_foundation_attributes.",
                    },
                    "foundation_depth": {
                        "type": "number",
                        "description": "Total foundation depth in inches (from top of slab to bottom of footing)"
                    },
                    "slab_thickness": {
                        "type": "number",
                        "description": "Concrete slab thickness in inches"
                    },
                    "footing_width": {
                        "type": "number",
                        "description": "Footing width in inches"
                    },
                    "garage_curb": {
                        "type": "boolean",
                        "description": "Create garage door curb (true) or remove it (false)"
                    },
                    "curb_width": {
                        "type": "number",
                        "description": "Garage curb width in inches (only used if garage_curb is true)"
                    },
                    "curb_height": {
                        "type": "number",
                        "description": "Garage curb height in inches (only used if garage_curb is true)"
                    },
                    "rebar_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) rebar/reinforcement options"
                    },
                    "top_bar_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) top footing bars"
                    },
                    "top_bar_diameter": {
                        "type": "number",
                        "description": "Top bar diameter in inches (e.g., 0.5 for #4 rebar)"
                    },
                    "top_bar_quantity": {
                        "type": "integer",
                        "description": "Number of top bars"
                    },
                    "bottom_bar_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) bottom footing bars"
                    },
                    "bottom_bar_diameter": {
                        "type": "number",
                        "description": "Bottom bar diameter in inches"
                    },
                    "bottom_bar_quantity": {
                        "type": "integer",
                        "description": "Number of bottom bars"
                    },
                    "slab_reinforcement_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) slab reinforcement"
                    },
                    "slab_reinforcement_type": {
                        "type": "string",
                        "description": "Slab reinforcement type (e.g., 'WWF' for welded wire fabric)"
                    },
                    "slab_reinforcement_spacing": {
                        "type": "number",
                        "description": "Slab reinforcement spacing in inches"
                    },
                    "anchor_bolts_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) anchor bolts and sill plate"
                    },
                    "bolt_size": {
                        "type": "string",
                        "description": "Anchor bolt length in inches (e.g., '10', '12', '14')"
                    },
                    "bolt_diameter": {
                        "type": "string",
                        "description": "Anchor bolt diameter (e.g., '1/2', '5/8')"
                    },
                    "washer_type": {
                        "type": "string",
                        "description": "Washer size (e.g., '2x2', '3x3')"
                    },
                    "bolt_spacing_ft": {
                        "type": "number",
                        "description": "Bolt spacing in feet on center"
                    },
                    "sill_width": {
                        "type": "number",
                        "description": "Sill plate width in inches"
                    },
                    "sill_thickness": {
                        "type": "number",
                        "description": "Sill plate thickness in inches"
                    },
                    "corner_distance": {
                        "type": "number",
                        "description": "Distance from corner to first bolt in inches"
                    },
                    "fpsf_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) Frost Protected Shallow Foundation (FPSF) insulation"
                    },
                    "insulation_type": {
                        "type": "string",
                        "description": "FPSF insulation type: 'Vertical Only', 'Vert. and Horz.', or 'None'"
                    },
                    "vertical_insulation": {
                        "type": "number",
                        "description": "Vertical insulation R-value"
                    },
                    "wing_insulation": {
                        "type": "number",
                        "description": "Horizontal wing insulation R-value"
                    },
                    "corner_insulation": {
                        "type": "number",
                        "description": "Corner insulation R-value"
                    },
                    "dim_a": {
                        "type": "number",
                        "description": "FPSF dimension A in inches"
                    },
                    "dim_b": {
                        "type": "number",
                        "description": "FPSF dimension B in inches"
                    },
                    "dim_c": {
                        "type": "number",
                        "description": "FPSF dimension C in inches"
                    },
                    "slab_insulation_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) slab insulation"
                    },
                    "slab_insulation": {
                        "type": "number",
                        "description": "Slab insulation R-value"
                    },
                    "subbase_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) subbase layer beneath slab"
                    },
                    "subbase_depth": {
                        "type": "number",
                        "description": "Subbase depth in inches"
                    },
                    "subbase_material": {
                        "type": "string",
                        "description": "Subbase material: 'Gravel', 'Stone1', or 'corrugated_metal'"
                    },
                    "drain_enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) perimeter drain"
                    }
                },
                "required": ["group_name"]
            },
        ),

        # ── Wall Tools (Medeek Wall Plugin) ────────────────────────────────

        types.Tool(
            name="create_medeek_wall",
            description=(
                "Create a single wall between two points using Medeek Wall Plugin. "
                "**USE THIS TOOL for any request involving: walls, wall framing, studs, exterior walls, interior walls.** "
                "\n\n"
                "**CRITICAL WORKFLOW for placing walls on a foundation:**\n"
                "1. FIRST call get_foundation_info to query the exact slab_top_z value from the model\n"
                "2. Use that slab_top_z value for the Z coordinate in start_point and end_point\n"
                "3. DO NOT assume the slab is at Z=0 or guess the slab thickness\n"
                "Example: get_foundation_info returns slab_top_z=-14.0, use [x, y, -14.0] for wall points.\n\n"
                "**CRITICAL - Wall Family Selection:**\n"
                "- **Rectangular (DEFAULT)**: Standard wall with flat top plate at consistent height. USE THIS unless user explicitly requests gables.\n"
                "- **Gable**: Wall with peaked top (triangle shape) to meet sloped roof. ONLY use if user specifically requests gable ends.\n"
                "- **Shed**: Wall with sloped top. ONLY use if explicitly requested.\n"
                "- **Hip**: Wall for hip roof. ONLY use if explicitly requested.\n"
                "**DO NOT create gables automatically** - default to Rectangular for all standard walls.\n\n"
                "Creates professional wall assemblies with proper framing, studs, plates, and sheathing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "start_point": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Wall start point [x, y, z] in inches"
                    },
                    "end_point": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Wall end point [x, y, z] in inches"
                    },
                    "wall_family": {
                        "type": "string",
                        "enum": ["Rectangular", "Gable", "Shed", "Hip"],
                        "description": "Wall family type. ALWAYS use 'Rectangular' (default) for standard walls with flat top plates. ONLY use 'Gable', 'Shed', or 'Hip' if user explicitly requests peaked/sloped walls."
                    },
                    "wall_type": {
                        "type": "string",
                        "enum": ["Int-Ext", "Int-Int"],
                        "description": "Wall type (Int-Ext for exterior, Int-Int for interior). Default: Int-Ext"
                    }
                },
                "required": ["start_point", "end_point"]
            },
        ),

        types.Tool(
            name="create_wall_perimeter",
            description=(
                "Create a complete wall perimeter from a polygon outline using Medeek Wall Plugin. "
                "**USE THIS TOOL to create walls around a foundation, building outline, or room perimeter.** "
                "\n\n"
                "**CRITICAL WORKFLOW for placing walls on a foundation:**\n"
                "1. FIRST call get_foundation_info to query the exact slab_top_z and outline_points\n"
                "2. Use the returned outline_points directly (already at correct Z) OR use slab_top_z for custom points\n"
                "3. DO NOT assume the slab is at Z=0 or guess dimensions\n"
                "Example: get_foundation_info returns outline_points=[[0,0,-14], [720,0,-14], ...], use those points directly.\n\n"
                "**CRITICAL - Wall Family Selection:**\n"
                "- **Rectangular (DEFAULT)**: Standard walls with flat top plate at consistent height. USE THIS unless user explicitly requests gables.\n"
                "- **Gable**: Walls with peaked tops (triangle shape) to meet sloped roof. ONLY use if user specifically requests gable ends.\n"
                "- **Shed/Hip**: ONLY use if explicitly requested.\n"
                "**DO NOT create gables automatically** - default to Rectangular for all standard building perimeters.\n\n"
                "Automatically creates walls along each edge of the polygon with proper corners and connections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "outline_points": {
                        "type": "array",
                        "description": "Ordered list of [x,y,z] points defining the perimeter. Minimum 3 points.",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "minItems": 3,
                    },
                    "wall_family": {
                        "type": "string",
                        "enum": ["Rectangular", "Gable", "Shed", "Hip"],
                        "description": "Wall family type. ALWAYS use 'Rectangular' (default) for standard walls with flat top plates. ONLY use 'Gable', 'Shed', or 'Hip' if user explicitly requests peaked/sloped walls."
                    },
                    "wall_type": {
                        "type": "string",
                        "enum": ["Int-Ext", "Int-Int"],
                        "description": "Wall type. Default: Int-Ext"
                    }
                },
                "required": ["outline_points"]
            },
        ),

        types.Tool(
            name="read_wall_attributes",
            description="Read all attributes from an existing Medeek Wall assembly. Returns all wall parameters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    }
                },
                "required": ["group_name"]
            },
        ),

        types.Tool(
            name="read_wall_attribute",
            description="Read a specific attribute from an existing Medeek Wall assembly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": "Name of the attribute to read"
                    }
                },
                "required": ["group_name", "attribute_name"]
            },
        ),

        types.Tool(
            name="modify_wall_attribute",
            description=(
                "Modify a Medeek Wall attribute after creation. Passes attribute_name and value directly to Medeek API - no conversion or interpretation.\n\n"
                "**CRITICAL - Value Format Rules:**\n"
                "- Dimensions/numbers: Pass as numeric values (e.g., 96.0, 12.0, -0.5)\n"
                "- Options/toggles: MUST pass as literal strings 'YES' or 'NO' (NOT true/false, NOT boolean)\n"
                "- Lumber sizes: Pass as strings (e.g., '2X4', '2X6', '2X8')\n"
                "- Material names: Pass as strings\n\n"
                "**Common Wall Attributes:**\n"
                "Dimensions (numeric values):\n"
                "- WALLHEIGHT: Wall height in inches (e.g., 96.0, 108.0)\n"
                "- WALLSHEATHVERTOFFSET_B: Sheathing vertical extension bottom in inches (can be negative, e.g., -0.5, 0.0, 2.0)\n"
                "- WALLSHEATHVERTOFFSET_T: Sheathing vertical extension top in inches (can be negative)\n"
                "- WALLCLADVERTOFFSET_B: Cladding vertical extension bottom in inches (can be negative)\n"
                "- WALLCLADVERTOFFSET_T: Cladding vertical extension top in inches (can be negative)\n"
                "- STUDSPACING: Stud spacing in inches (12, 16, 19.2, or 24)\n\n"
                "Options (string 'YES' or 'NO'):\n"
                "- WALLSHEATHOPTION: Enable/disable wall sheathing (value='YES' or value='NO')\n"
                "- WALLCLADOPTION: Enable/disable wall cladding (value='YES' or value='NO')\n"
                "- WALLGIRTOPTION: Enable/disable wall girts (value='YES' or value='NO')\n\n"
                "Lumber/Material (string values):\n"
                "- STUDWIDTH: Stud width (value='2X4', value='2X6', or value='2X8')\n"
                "- PLATEWIDTH: Top/bottom plate width (value='2X4', value='2X6', or value='2X8')\n"
                "- GIRTWIDTH: Girt width (value='2X4' or value='2X6')\n"
                "- WALLSHEATHMAT: Sheathing material name (string)\n"
                "- WALLCLADMAT: Cladding material name (string)\n\n"
                "**Usage Examples:**\n"
                "- Change wall height: attribute_name='WALLHEIGHT', value=108.0\n"
                "- Enable sheathing: attribute_name='WALLSHEATHOPTION', value='YES'\n"
                "- Change studs: attribute_name='STUDWIDTH', value='2X6'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name to modify"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": "Medeek wall attribute name (see tool description for common attributes)"
                    },
                    "value": {
                        "description": "Attribute value - EXACT format required: numeric for dimensions (e.g., 96.0), string 'YES' or 'NO' for options (NOT true/false), string for lumber sizes (e.g., '2X6')"
                    },
                    "regenerate": {
                        "type": "boolean",
                        "description": "Regenerate the wall after modifying (true). Set to false for batch changes to avoid regenerating after each change. Default: true"
                    }
                },
                "required": ["group_name", "attribute_name", "value"]
            },
        ),

        types.Tool(
            name="get_wall_info",
            description=(
                "Query authoritative wall geometry and dimensions from an existing Medeek Wall. "
                "Returns critical information needed for placing trusses, roofs, or other elements on top of walls.\n\n"
                "**CRITICAL WORKFLOW for placing trusses on walls:**\n"
                "1. FIRST call get_wall_info to query the exact top_plate_z and wall dimensions\n"
                "2. Use the returned top_plate_z for truss placement (DO NOT calculate or guess)\n"
                "3. Use wall_start and wall_end to calculate proper truss span\n\n"
                "**Returned Information:**\n"
                "- top_plate_z: Z coordinate of the top of the wall top plate (in inches)\n"
                "- base_z: Z coordinate of the bottom of the wall\n"
                "- wall_height: Total wall height in inches\n"
                "- wall_start: [x,y,z] start point of wall\n"
                "- wall_end: [x,y,z] end point of wall\n"
                "- wall_length: Wall length in inches\n"
                "- stud_spacing: Stud spacing in inches\n"
                "- plate_width: Top/bottom plate lumber size (e.g., '2X4', '2X6')"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name to query (optional - uses selection if not provided)"
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="add_window",
            description=(
                "Add a SINGLE window to an existing Medeek Wall. "
                "Creates window opening with optional window unit, trim, and casing. "
                "**Important: Each call creates ONE window. For multiple windows, make separate calls (can be done in parallel).**"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name to add window to"
                    },
                    "location": {
                        "type": "number",
                        "description": "Distance in inches from wall start point to the center of the window placement"
                    },
                    "width": {
                        "type": "number",
                        "description": "Window width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Window height in inches"
                    },
                    "geometry": {
                        "type": "string",
                        "enum": ["Rectangle", "Half Round", "Arch", "Gothic Arch", "Oval", "Octagon", "Hexagon", "Trapezoid", "Pentagon"],
                        "description": "Window opening geometry/shape. Default: Rectangle"
                    },
                    "install_window": {
                        "type": "boolean",
                        "description": "Install the window unit in the window opening (true) or create rough opening only (false). Default: true"
                    },
                    "exterior_trim": {
                        "type": "boolean",
                        "description": "Install exterior trim around the window opening. Default: true"
                    },
                    "interior_casing": {
                        "type": "boolean",
                        "description": "Install interior casing around the window opening. Default: true"
                    }
                },
                "required": ["group_name", "location", "width", "height"]
            },
        ),

        types.Tool(
            name="read_window_attributes",
            description="Read attributes from a window in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_name": {
                        "type": "string",
                        "description": "Window name (e.g., 'WINDOW1', 'WINDOW2')"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name (optional - uses selection if not provided)"
                    }
                },
                "required": ["window_name"]
            },
        ),

        types.Tool(
            name="add_door",
            description=(
                "Add a SINGLE door to an existing Medeek Wall. "
                "Creates door opening with optional door unit, trim, and casing. "
                "**Important: Each call creates ONE door. For multiple doors, make separate calls (can be done in parallel).**"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name to add door to"
                    },
                    "location": {
                        "type": "number",
                        "description": "Distance in inches from wall start point to the center of the door placement"
                    },
                    "width": {
                        "type": "number",
                        "description": "Door width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Door height in inches"
                    },
                    "geometry": {
                        "type": "string",
                        "enum": ["Rectangle", "Arch"],
                        "description": "Door opening geometry/shape. Rectangle (rectangular) or Arch (arched top). Default: Rectangle"
                    },
                    "install_door": {
                        "type": "boolean",
                        "description": "Install the door unit in the door opening (true) or create rough opening only (false). Default: true"
                    },
                    "exterior_trim": {
                        "type": "boolean",
                        "description": "Install exterior trim around the door opening. Default: true"
                    },
                    "interior_casing": {
                        "type": "boolean",
                        "description": "Install interior casing around the door opening. Default: true"
                    }
                },
                "required": ["group_name", "location", "width", "height"]
            },
        ),

        types.Tool(
            name="read_door_attributes",
            description="Read attributes from a door in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "door_name": {
                        "type": "string",
                        "description": "Door name (e.g., 'DOOR1', 'DOOR2')"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name (optional - uses selection if not provided)"
                    }
                },
                "required": ["door_name"]
            },
        ),

        types.Tool(
            name="add_garage_door",
            description=(
                "Add a SINGLE garage door to an existing Medeek Wall. "
                "Creates garage door opening with optional door unit, trim, and casing. "
                "**Important: Each call creates ONE garage door. For multiple garage doors, make separate calls (can be done in parallel).**"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name to add garage door to"
                    },
                    "location": {
                        "type": "number",
                        "description": "Distance in inches from wall start point to the center of the garage door placement"
                    },
                    "width": {
                        "type": "number",
                        "description": "Garage door width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Garage door height in inches"
                    },
                    "geometry": {
                        "type": "string",
                        "enum": ["Rectangle", "Arch", "Dutch"],
                        "description": "Garage door opening geometry/shape. Rectangle (rectangular), Arch (arched top), or Dutch (divided). Default: Rectangle"
                    },
                    "install_door": {
                        "type": "boolean",
                        "description": "Install the garage door unit in the opening (true) or create rough opening only (false). Default: true"
                    },
                    "exterior_trim": {
                        "type": "boolean",
                        "description": "Install exterior trim around the garage door opening. Default: true"
                    },
                    "interior_casing": {
                        "type": "boolean",
                        "description": "Install interior casing around the garage door opening. Default: true"
                    }
                },
                "required": ["group_name", "location", "width", "height"]
            },
        ),

        types.Tool(
            name="read_garage_attributes",
            description="Read attributes from a garage door in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "garage_name": {
                        "type": "string",
                        "description": "Garage door name (e.g., 'GARAGE1', 'GARAGE2')"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name (optional - uses selection if not provided)"
                    }
                },
                "required": ["garage_name"]
            },
        ),

        types.Tool(
            name="add_column",
            description=(
                "Add a column to an existing Medeek Wall. "
                "Supports 7 material types: STEEL, WOOD, CONCRETE, BRICK, STONE, ALUMINUM, COMPOSITE."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name to add column to"
                    },
                    "column_material": {
                        "type": "string",
                        "enum": ["STEEL", "WOOD", "CONCRETE", "BRICK", "STONE", "ALUMINUM", "COMPOSITE"],
                        "description": "Column material type"
                    },
                    "position": {
                        "type": "number",
                        "description": "Distance from wall start in inches"
                    },
                    "width": {
                        "type": "number",
                        "description": "Column width in inches"
                    },
                    "depth": {
                        "type": "number",
                        "description": "Column depth in inches"
                    }
                },
                "required": ["wall_group_name", "column_material", "position", "width", "depth"]
            },
        ),

        types.Tool(
            name="read_column_attributes",
            description="Read attributes from a column in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "column_index": {
                        "type": "number",
                        "description": "Column index (0-based)"
                    }
                },
                "required": ["wall_group_name", "column_index"]
            },
        ),

        types.Tool(
            name="get_wall_info",
            description=(
                "Get wall information from an existing Medeek Wall assembly. "
                "Returns authoritative values from Medeek attributes (not bounding box geometry). "
                "**CRITICAL: USE THIS TOOL to query the exact top_plate_z value before placing trusses on walls.** "
                "This tool reads directly from the Medeek Wall Plugin's stored attributes to provide accurate positioning data.\n\n"
                "**Typical workflow:**\n"
                "1. User asks to add trusses to existing walls\n"
                "2. Call get_wall_info with wall group name (optional - will find any wall if omitted)\n"
                "3. Use the returned `top_plate_z` value as the origin Z for truss placement\n"
                "4. Use `wall_length` and `wall_start`/`wall_end` for truss geometry\n\n"
                "**Returned information:**\n"
                "- top_plate_z: Exact Z position of the top of the top plate (use this for truss placement)\n"
                "- base_z: Z position of the wall base\n"
                "- wall_height: Wall height in inches\n"
                "- wall_length: Wall length in inches\n"
                "- wall_start: Start point [x, y, z]\n"
                "- wall_end: End point [x, y, z]\n"
                "- stud_width, stud_spacing, plate_width: Framing details"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name (optional - if not provided, will find any wall assembly in the model)"
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="read_truss_attributes",
            description="Read all attributes from a Medeek Truss assembly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Truss group name (optional - will find any truss if not provided)"
                    }
                },
                "required": []
            },
        ),

        types.Tool(
            name="read_truss_attribute",
            description="Read a single attribute from a Medeek Truss assembly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "Truss attribute name to read"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Truss group name (optional - will find any truss if not provided)"
                    }
                },
                "required": ["attribute_name"]
            },
        ),

        types.Tool(
            name="modify_truss_attribute",
            description=(
                "Modify a SINGLE Medeek Truss attribute. **IMPORTANT: When changing multiple related attributes (e.g., enabling advanced roof options AND sheathing), use modify_truss instead to avoid regeneration issues.**\n\n"
                "**KNOWN LIMITATION:** The Medeek API may require the edit UI to be opened manually once before modifications work. If this fails, inform the user to open the Medeek edit dialog once, then retry.\n\n"
                "This tool modifies one attribute at a time. Each call with regenerate=true causes the truss to rebuild, which can reset other options. "
                "For enabling roof features like sheathing, use the batch modify_truss tool instead.\n\n"
                "**CRITICAL - Value Format Rules:**\n"
                "- Dimensions/numbers: Pass as numeric values (e.g., 24.0, 5.5, 3.5)\n"
                "- Options/toggles: MUST pass as literal strings 'YES' or 'NO' (NOT true/false, NOT boolean, NOT 1/0)\n"
                "- Sheathing thickness: Pass as fraction string (e.g., '15/32', '1/2') - will be auto-converted to decimal\n"
                "- Examples: SHEATHING_OPTION='YES', FASCIA_OPTION='NO', RAISEDHEEL='YES'\n\n"
                "**Common Truss Attributes (from medeek_truss_param dictionary):**\n"
                "Dimensions (numeric values):\n"
                "- OVERHANGL: Left overhang in inches (e.g., 12.0, 18.0, 24.0)\n"
                "- OVERHANGR: Right overhang in inches (e.g., 12.0, 18.0, 24.0)\n"
                "- TCD: Top chord depth in inches (3.5=2x4, 5.5=2x6, 7.25=2x8)\n"
                "- BCD: Bottom chord depth in inches (3.5=2x4, 5.5=2x6, 7.25=2x8)\n"
                "- WEBD: Web depth in inches (3.5=2x4, 5.5=2x6)\n"
                "- PLY: Number of plies (1, 2, or 3)\n"
                "- PITCH: Roof pitch (e.g., 6.0 for 6:12, 8.0 for 8:12)\n"
                "- SPAN: Truss span in inches\n"
                "- USRHH: Raised heel height in inches (when RAISEDHEEL='YES')\n"
                "- TRUSS_SPACING: Truss spacing in inches on-center (e.g., 16.0, 24.0)\n\n"
                "Options (string 'YES' or 'NO'):\n"
                "- RAISEDHEEL: Raised heel option (value='YES' or value='NO')\n"
                "- SHEATHING_OPTION: Enable/disable sheathing (value='YES' or value='NO')\n"
                "- FASCIA_OPTION: Enable/disable fascia (value='YES' or value='NO')\n"
                "- RAKEBOARD_OPTION: Enable/disable rake boards (value='YES' or value='NO')\n"
                "- ROOFCLADDING_OPTION: Enable/disable roof cladding (value='YES' or value='NO')\n"
                "- GABLEWALL_OPTION: Enable/disable gable walls (value='YES' or value='NO')\n\n"
                "**Usage Examples:**\n"
                "- Change overhang: attribute_name='OVERHANGL', value=24.0\n"
                "- Enable sheathing: attribute_name='SHEATHING_OPTION', value='YES'\n"
                "- Disable fascia: attribute_name='FASCIA_OPTION', value='NO'\n"
                "- Change lumber: attribute_name='TCD', value=5.5"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Truss group name to modify (optional - will find any truss if not provided)"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": "Medeek truss attribute name - see tool description for available attributes"
                    },
                    "value": {
                        "description": "Attribute value - EXACT format required: numeric for dimensions (e.g., 24.0), string 'YES' or 'NO' for options (NOT true/false)"
                    },
                    "regenerate": {
                        "type": "boolean",
                        "description": "Regenerate the truss geometry after modifying. Default: true. Set false for batch changes."
                    }
                },
                "required": ["attribute_name", "value"]
            },
        ),

        types.Tool(
            name="modify_truss",
            description=(
                "Modify multiple Medeek Truss attributes at once (batch modification). **USE THIS TOOL when enabling roof features like sheathing, fascia, or cladding.**\n\n"
                "**KNOWN LIMITATION - Medeek API:**\n"
                "The Medeek Truss Plugin API may require the edit UI to be opened manually once before attribute modifications work properly. "
                "If modifications don't appear, inform the user they may need to: (1) Right-click the truss assembly, (2) Select 'Edit Truss Assembly', (3) Close the dialog, (4) Then retry the modification.\n\n"
                "**CRITICAL - Why use this tool:**\n"
                "When you modify truss attributes one at a time with regenerate=true, the Medeek plugin resets options like ADVROOFOPTIONS and SHEATHING_OPTION back to defaults. "
                "This tool sets ALL attributes with regen=false, then regenerates ONCE at the end with all changes applied together.\n\n"
                "**AUTOMATIC BEHAVIOR - NO NEED TO SET adv_roof_options:**\n"
                "If you pass ANY advanced feature (sheathing, fascia, cladding, gutters, etc.), the tool AUTOMATICALLY enables adv_roof_options='YES' for you. "
                "You do NOT need to explicitly pass adv_roof_options='YES' - just pass the features you want.\n\n"
                "**Common use cases:**\n"
                "- Add roof sheathing: Pass sheathing_option='YES' + sheathing_thickness='15/32' (adv_roof_options auto-enabled)\n"
                "- Add fascia boards: Pass fascia_option='YES' + fascia_width=7.25 (adv_roof_options auto-enabled)\n"
                "- Enable multiple roof features: Pass multiple parameters in one call\n\n"
                "**Value Format Rules:**\n"
                "- Dimensions/numbers: Pass as numeric values (e.g., 24.0, 5.5, 3.5)\n"
                "- Options/toggles: MUST pass as literal strings 'YES' or 'NO' (NOT true/false)\n\n"
                "**Example workflow to add sheathing:**\n"
                "modify_truss(group_name='COMMON_TRUSS_ASSEMBLY_1', sheathing_option='YES', sheathing_thickness='15/32')"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Truss group name to modify (required)"
                    },
                    "adv_roof_options": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable advanced roof options. NOTE: This is AUTOMATICALLY set to 'YES' if you pass any advanced feature (sheathing, fascia, etc.). You do NOT need to explicitly pass this parameter."
                    },
                    "overhang_left": {
                        "type": "number",
                        "description": "Left-side eave overhang in inches"
                    },
                    "overhang_right": {
                        "description": "Right-side eave overhang. Use 'SAME AS LEFT' or specify inches as number."
                    },
                    "top_chord_depth": {
                        "type": "number",
                        "description": "Top chord member depth in inches (3.5=2x4, 5.5=2x6, 7.25=2x8)"
                    },
                    "bottom_chord_depth": {
                        "type": "number",
                        "description": "Bottom chord member depth in inches"
                    },
                    "web_depth": {
                        "type": "number",
                        "description": "Web member depth in inches"
                    },
                    "ply": {
                        "type": "number",
                        "description": "Truss ply count (number of plies)"
                    },
                    "raised_heel": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable raised heel configuration"
                    },
                    "raised_heel_height": {
                        "type": "number",
                        "description": "Custom raised heel height in inches"
                    },
                    "truss_spacing": {
                        "type": "number",
                        "description": "Truss spacing in inches on-center"
                    },
                    "gable_truss_input": {
                        "type": "string",
                        "enum": ["YES", "NO", "FRONT"],
                        "description": "Gable truss configuration"
                    },
                    "vert_spacing": {
                        "type": "number",
                        "description": "Vertical spacing for web layout in inches"
                    },
                    "sheathing_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable roof sheathing (requires adv_roof_options='YES')"
                    },
                    "sheathing_thickness": {
                        "type": "string",
                        "enum": ["7/16", "15/32", "1/2", "19/32", "5/8", "23/32", "3/4"],
                        "description": "Roof sheathing thickness as fraction (e.g., '15/32', '1/2'). Automatically converted to decimal."
                    },
                    "gable_wall_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable gable wall framing"
                    },
                    "fascia_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable fascia boards (requires adv_roof_options='YES')"
                    },
                    "fascia_type": {
                        "type": "string",
                        "enum": ["DROP", "FLUSH", "BEVEL"],
                        "description": "Fascia type/configuration"
                    },
                    "fascia_width": {
                        "type": "number",
                        "description": "Fascia width in inches"
                    },
                    "fascia_depth": {
                        "type": "number",
                        "description": "Fascia depth in inches"
                    },
                    "rakeboard_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable rake boards"
                    },
                    "overhang_gable": {
                        "type": "number",
                        "description": "Gable-end overhang dimension in inches"
                    },
                    "rake_width": {
                        "type": "number",
                        "description": "Rake board width in inches"
                    },
                    "rake_depth": {
                        "type": "number",
                        "description": "Rake board depth in inches"
                    },
                    "outlooker_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable outlooker framing"
                    },
                    "outlooker_spacing": {
                        "type": "number",
                        "description": "Outlooker spacing in inches"
                    },
                    "outlooker_size": {
                        "type": "string",
                        "enum": ["2x4", "2x6"],
                        "description": "Outlooker member size"
                    },
                    "outlooker_orient": {
                        "type": "string",
                        "enum": ["HORIZONTAL", "VERTICAL"],
                        "description": "Outlooker orientation"
                    },
                    "outlooker_peak": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Extend outlooker to peak"
                    },
                    "heelblock_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable heel blocks"
                    },
                    "heelblock_orient": {
                        "type": "string",
                        "enum": ["ANGLED", "VERTICAL"],
                        "description": "Heel block orientation"
                    },
                    "roofcladding_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable roof cladding"
                    },
                    "roofclad_ext": {
                        "type": "number",
                        "description": "Roof cladding extension in inches"
                    },
                    "ridgecap_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable ridge cap"
                    },
                    "wallcladding_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable wall cladding for gable walls"
                    },
                    "soffit_cut": {
                        "type": "string",
                        "enum": ["NO", "FLUSH", "0.25", "0.375", "0.5", "0.625", "0.75", "1.0", "1.5"],
                        "description": "Soffit cut style"
                    },
                    "roof_return": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable roof return"
                    },
                    "return_type": {
                        "type": "string",
                        "enum": ["Hip", "Gable", "Full"],
                        "description": "Roof return type/configuration"
                    },
                    "pitch3": {
                        "type": "string",
                        "description": "Roof return pitch value"
                    },
                    "return_ext": {
                        "type": "number",
                        "description": "Roof return extension in inches"
                    },
                    "return_length": {
                        "type": "number",
                        "description": "Roof return length in inches"
                    },
                    "roof_batten": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable roof battens"
                    },
                    "gypsum_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable gypsum ceiling"
                    },
                    "gutter_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable gutters"
                    },
                    "gutter_type": {
                        "type": "string",
                        "description": "Gutter type/profile"
                    },
                    "gutter_voffset": {
                        "type": "number",
                        "description": "Vertical offset for gutter placement in inches"
                    },
                    "gutter_ext": {
                        "type": "number",
                        "description": "Gutter extension in inches"
                    },
                    "downspout_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable downspout geometry"
                    },
                    "dsp_length": {
                        "type": "number",
                        "description": "Downspout length in inches"
                    },
                    "dsp_type": {
                        "type": "string",
                        "enum": ["RECTANGLE", "ROUND"],
                        "description": "Downspout type/profile"
                    },
                    "gutter_wrap_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable gutter wrap"
                    },
                    "insul_option": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Enable insulation"
                    },
                    "wallsheath_mat": {
                        "type": "string",
                        "description": "Wall sheathing material"
                    },
                    "wallclad_mat": {
                        "type": "string",
                        "description": "Wall cladding material"
                    },
                    "roofsheath_mat": {
                        "type": "string",
                        "description": "Roof sheathing material"
                    },
                    "roofclad_mat": {
                        "type": "string",
                        "description": "Roof cladding material"
                    },
                    "wallsheath_thk": {
                        "description": "Wall sheathing thickness. Can be fraction string (e.g., '15/32', '1/2') or decimal number. Automatically converted to decimal."
                    },
                    "wallclad_thk": {
                        "type": "number",
                        "description": "Wall cladding thickness in inches"
                    },
                    "roofclad_thk": {
                        "type": "number",
                        "description": "Roof cladding thickness in inches"
                    }
                },
                "required": ["group_name"]
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
                "Use with care — this can modify or delete model data. "
                "\n\n**IMPORTANT: ALWAYS prefer specialized MCP tools over execute_ruby when available:**\n"
                "- Creating constructions: Use create_foundation, create_wall_perimeter, create_roof_truss (NOT execute_ruby)\n"
                "- Modifying constructions: Use modify_truss_attribute, modify_wall_attribute, modify_foundation (NOT execute_ruby)\n"
                "- Reading construction data: Use read_truss_attributes, read_wall_attributes, get_wall_info, get_foundation_info (NOT execute_ruby)\n"
                "- Adding features: Use add_window, add_door, add_garage_door (NOT execute_ruby)\n\n"
                "Only use execute_ruby for tasks that don't have a specialized tool (e.g., querying general model state, debugging, custom geometry)."
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

        elif name == "create_wall":
            return ok(await su_post("/construction/wall", arguments))

        elif name == "create_foundation":
            return ok(await su_post("/construction/foundation", arguments))

        elif name == "read_foundation_attributes":
            return ok(await su_post("/construction/foundation/read_attributes", arguments))

        elif name == "read_foundation_attribute":
            return ok(await su_post("/construction/foundation/read_attribute", arguments))

        elif name == "get_foundation_info":
            return ok(await su_post("/construction/foundation/info", arguments))

        elif name == "modify_foundation":
            return ok(await su_post("/construction/foundation/modify", arguments))

        elif name == "create_medeek_wall":
            return ok(await su_post("/construction/wall/create", arguments))

        elif name == "create_wall_perimeter":
            return ok(await su_post("/construction/wall/perimeter", arguments))

        elif name == "read_wall_attributes":
            return ok(await su_post("/construction/wall/read_attributes", arguments))

        elif name == "read_wall_attribute":
            return ok(await su_post("/construction/wall/read_attribute", arguments))

        elif name == "modify_wall_attribute":
            return ok(await su_post("/construction/wall/modify", arguments))

        elif name == "get_wall_info":
            return ok(await su_post("/construction/wall/info", arguments))

        elif name == "add_window":
            return ok(await su_post("/construction/wall/window", arguments))

        elif name == "read_window_attributes":
            return ok(await su_post("/construction/wall/window/read_attributes", arguments))

        elif name == "add_door":
            return ok(await su_post("/construction/wall/door", arguments))

        elif name == "read_door_attributes":
            return ok(await su_post("/construction/wall/door/read_attributes", arguments))

        elif name == "add_garage_door":
            return ok(await su_post("/construction/wall/garage", arguments))

        elif name == "read_garage_attributes":
            return ok(await su_post("/construction/wall/garage/read_attributes", arguments))

        elif name == "add_column":
            return ok(await su_post("/construction/wall/column", arguments))

        elif name == "read_column_attributes":
            return ok(await su_post("/construction/wall/column/read_attributes", arguments))

        elif name == "get_wall_info":
            return ok(await su_post("/construction/wall/info", arguments))

        elif name == "read_truss_attributes":
            return ok(await su_post("/construction/truss/read_attributes", arguments))

        elif name == "read_truss_attribute":
            return ok(await su_post("/construction/truss/read_attribute", arguments))

        elif name == "modify_truss_attribute":
            return ok(await su_post("/construction/truss/modify", arguments))

        elif name == "modify_truss":
            return ok(await su_post("/construction/truss/modify_batch", arguments))

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
