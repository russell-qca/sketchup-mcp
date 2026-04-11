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
                "DIRECTLY create professional engineered roof trusses in SketchUp using Medeek Truss Plugin. "
                "IMPORTANT: ONE CALL creates ALL trusses - use the 'count' parameter to specify how many. "
                "For example, to create 5 trusses, call this tool ONCE with count=5, NOT 5 separate calls. "
                "Supports 14 truss types: king, queen, fink, howe, fan, mod_queen, double_fink, double_howe, "
                "mod_fan, triple_fink, triple_howe, quad_fink, quad_howe, penta_howe. "
                "Creates complete 3D models with proper web patterns, angled members, and realistic connections.\n\n"
                "CRITICAL WORKFLOW RULES:\n"
                "1. NEVER create test or exploratory geometry in the model to verify calculations. All geometry decisions must be derived from querying existing model data (bounding boxes, entity positions, tags, etc.) BEFORE creating any final geometry. If verification is needed, do it through Ruby queries using execute_ruby - never by placing temporary objects in the model.\n\n"
                "2. After calling create_roof_truss, ALWAYS use execute_ruby to audit the top-level model entities for any residual or misplaced groups (e.g., individual Fink_Truss_* groups not inside TRUSS_ASSEMBLY, or groups at incorrect Z elevations or outside expected bounds). Delete any stray groups before reporting completion.\n\n"
                "3. If a 'layer' parameter was provided, immediately use execute_ruby after truss creation to assign the TRUSS_ASSEMBLY group to that tag/layer. Do not leave it on Layer0."
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
                        "description": "PREFERRED when framing exists: Provide the 4 outer corner points from the top of the top plate face. Format: [[x1,y1,z1], [x2,y2,z2], [x3,y3,z3], [x4,y4,z4]] in order front-left, front-right, back-right, back-left. IMPORTANT: Just pass the face corners AS-IS - do NOT calculate or adjust for truss positions. Medeek automatically determines truss count and placement based on the parallelogram.",
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
                "Supports 4 wall families (Rectangular, Gable, Shed, Hip) and 2 wall types (Int-Ext, Int-Int). "
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
                        "description": "Wall family type. Default: Rectangular"
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
                        "description": "Wall family type. Default: Rectangular"
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
            description="Modify a parameter on an existing Medeek Wall. Use to change wall properties after creation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": "Parameter to modify"
                    },
                    "attribute_value": {
                        "description": "New value for the parameter"
                    }
                },
                "required": ["group_name", "attribute_name", "attribute_value"]
            },
        ),

        types.Tool(
            name="add_window",
            description=(
                "Add a window to an existing Medeek Wall. "
                "Supports 9 geometry types: RECT (rectangular), ARCH (arched), RAKE (raked), "
                "ELLIP (elliptical), TRAPZ (trapezoidal), CIRCL (circular), TRIANGLE (triangular), "
                "POLYGON (polygonal), LWRARCH (lower arched)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name to add window to"
                    },
                    "window_type": {
                        "type": "string",
                        "enum": ["RECT", "ARCH", "RAKE", "ELLIP", "TRAPZ", "CIRCL", "TRIANGLE", "POLYGON", "LWRARCH"],
                        "description": "Window geometry type"
                    },
                    "position": {
                        "type": "number",
                        "description": "Distance from wall start in inches"
                    },
                    "width": {
                        "type": "number",
                        "description": "Window width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Window height in inches"
                    },
                    "sill_height": {
                        "type": "number",
                        "description": "Height of window sill from floor in inches"
                    }
                },
                "required": ["wall_group_name", "window_type", "position", "width", "height"]
            },
        ),

        types.Tool(
            name="read_window_attributes",
            description="Read attributes from a window in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "window_index": {
                        "type": "number",
                        "description": "Window index (0-based)"
                    }
                },
                "required": ["wall_group_name", "window_index"]
            },
        ),

        types.Tool(
            name="add_door",
            description=(
                "Add a door to an existing Medeek Wall. "
                "Supports 2 geometry types: RECT (rectangular), ARCH (arched)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name to add door to"
                    },
                    "door_type": {
                        "type": "string",
                        "enum": ["RECT", "ARCH"],
                        "description": "Door geometry type"
                    },
                    "position": {
                        "type": "number",
                        "description": "Distance from wall start in inches"
                    },
                    "width": {
                        "type": "number",
                        "description": "Door width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Door height in inches"
                    }
                },
                "required": ["wall_group_name", "door_type", "position", "width", "height"]
            },
        ),

        types.Tool(
            name="read_door_attributes",
            description="Read attributes from a door in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "door_index": {
                        "type": "number",
                        "description": "Door index (0-based)"
                    }
                },
                "required": ["wall_group_name", "door_index"]
            },
        ),

        types.Tool(
            name="add_garage_door",
            description=(
                "Add a garage door to an existing Medeek Wall. "
                "Supports 3 geometry types: RECT (rectangular), ARCH (arched), RAKE (raked)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name to add garage door to"
                    },
                    "garage_type": {
                        "type": "string",
                        "enum": ["RECT", "ARCH", "RAKE"],
                        "description": "Garage door geometry type"
                    },
                    "position": {
                        "type": "number",
                        "description": "Distance from wall start in inches"
                    },
                    "width": {
                        "type": "number",
                        "description": "Garage door width in inches"
                    },
                    "height": {
                        "type": "number",
                        "description": "Garage door height in inches"
                    }
                },
                "required": ["wall_group_name", "garage_type", "position", "width", "height"]
            },
        ),

        types.Tool(
            name="read_garage_attributes",
            description="Read attributes from a garage door in a Medeek Wall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "wall_group_name": {
                        "type": "string",
                        "description": "Wall group name"
                    },
                    "garage_index": {
                        "type": "number",
                        "description": "Garage door index (0-based)"
                    }
                },
                "required": ["wall_group_name", "garage_index"]
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

        # ── Execute Ruby ───────────────────────────────────────────────────

        types.Tool(
            name="execute_ruby",
            description=(
                "Execute arbitrary Ruby code inside SketchUp. "
                "The code runs in the context of the SU_MCP module and has full access "
                "to the SketchUp Ruby API (Sketchup, Geom, UI, etc.). "
                "Returns the result of the last expression and any puts/print output. "
                "Use with care — this can modify or delete model data. "
                "\n\n**IMPORTANT: Do NOT use this tool to create foundations, slabs, footers, or trusses.** "
                "Use the specialized construction tools instead: create_foundation for slabs/footers, create_roof_truss for trusses."
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
