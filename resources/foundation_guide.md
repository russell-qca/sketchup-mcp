# Foundation Creation Guide - Medeek Foundation Plugin API

## CRITICAL: How the Medeek Foundation API Works

### MANDATORY TWO-STEP WORKFLOW

**When a user requests a foundation with custom parameters:**

**Step 1: create_foundation - GEOMETRY ONLY**
- ONLY pass `outline_points` (the corner points)
- DO NOT pass any other parameters (depth, rebar, bolts, etc.)

**Step 2: modify_foundation - ALL CUSTOM PARAMETERS**
- Pass the `group_name` from Step 1
- Pass ALL custom parameters (depth, thickness, rebar, bolts, etc.) in ONE call
- Do NOT make multiple modify calls - combine all changes into one

### The Medeek API is Different from Regular SketchUp
**YOU can only pass the geometry defining the area of the slab when creating a foundation.
Do not try to pass any other parameters with this call.**

**Do not ever delete and rebuild the foundation unless asked very specifically to do so.  All attribute changes
should be managed on the existing slab by using modify_foundation.**

### Medeek Foundation Workflow (MANDATORY - NO EXCEPTIONS)

```
STEP 1: Create with DEFAULT settings
  └─> Call sog_draw(points) with ONLY geometry
  └─> Returns foundation with default 24" depth, 4" slab, 16" footing
  └─> Do not pass any parameters other than the geometry
  

STEP 2: Modify parameters (ONLY AFTER creation)
  └─> Call sog_set_attribute(param, value, group, regen)
  └─> Repeat for each parameter you want to change
  └─> Set regen=true on the LAST attribute
  └─> Do not call sog_regen as this is not needed.

RESULT: Custom foundation with your specifications
```

## Two Tools: Create vs Modify

### create_foundation - For NEW Foundations Only
**Use this tool ONLY when creating a brand new foundation from scratch.**

### modify_foundation - For EXISTING Foundations
**Use this tool to change parameters on foundations that already exist.**
**NEVER delete and recreate a foundation to make changes - use modify_foundation instead!**

## Using the create_foundation Tool

**CRITICAL: create_foundation should ONLY receive the outline_points (geometry).**

### ✅ CORRECT: Create with Geometry Only, Then Modify

**User request:** "Create a 40' × 60' concrete slab with 32" footer depth and 5/8" anchor bolts"

**Step 1: Create foundation with ONLY geometry**
```json
{
  "outline_points": [[0,0,0], [480,0,0], [480,720,0], [0,720,0]]
}
```

**This returns:**
```json
{
  "status": "created",
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500",
  ...
}
```

**Step 2: Modify foundation with ALL custom parameters**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500",
  "foundation_depth": 32,
  "anchor_bolts_enabled": true,
  "bolt_diameter": "5/8"
}
```

**Result:** Foundation with 40'×60' dimensions, 32" footer depth, and 5/8" anchor bolts

### ❌ WRONG: Passing Parameters to create_foundation

**NEVER do this:**
```json
{
  "outline_points": [[0,0,0], [480,0,0], [480,720,0], [0,720,0]],
  "foundation_depth": 32,
  "anchor_bolts_enabled": true
}
```

**Why this is wrong:**
- create_foundation should ONLY receive outline_points
- All other parameters MUST be set via modify_foundation
- This ensures proper Medeek API workflow

### ❌ WRONG: Calling create_foundation Multiple Times

**NEVER do this:**
```
1. Call create_foundation with outline_points
2. Call create_foundation again with different parameters
```

**Why this is wrong:**
- Creates MULTIPLE foundations (one per call)
- Use modify_foundation to change parameters, not create_foundation

## Using the modify_foundation Tool

**Use this tool to change parameters on an EXISTING foundation.**

### ✅ CORRECT: Modify Existing Foundation

**User request:** "Change the foundation depth to 36 inches"

**Step 1: Get the foundation group_name** (from create_foundation response or read_foundation_attributes)
```
group_name: "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308"
```

**Step 2: Call modify_foundation with ONLY the parameters you want to change**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308",
  "foundation_depth": 36
}
```

**Result:** The existing foundation is modified to 36" depth - all other parameters remain unchanged

### ✅ CORRECT: Add Rebar to Existing Foundation

**User request:** "Add rebar to the foundation"

```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308",
  "rebar_enabled": true,
  "bottom_bar_enabled": true,
  "bottom_bar_diameter": 0.5,
  "bottom_bar_quantity": 2,
  "slab_reinforcement_enabled": true,
  "slab_reinforcement_type": "WWF"
}
```

**Result:** The existing foundation now has rebar - no need to delete and recreate!

### ❌ WRONG: Deleting and Recreating to Modify

**NEVER do this:**
```
1. Delete the existing foundation
2. Call create_foundation with new parameters
```

**Why this is wrong:**
- Unnecessarily destroys existing work
- Wastes time and API calls
- User loses the foundation group_name reference
- Very confusing workflow

**DO THIS INSTEAD:**
```
1. Call modify_foundation with the parameters you want to change
```

## Reading Foundation Attributes

### Use read_foundation_attribute for Single Values

**User asks:** "What's the anchor bolt size on this foundation?"

**Correct approach:**
```json
{
  "attribute_name": "BOLTSIZE",
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308"
}
```

**Response:**
```json
{
  "status": "success",
  "value": "1/2\""
}
```

### Use read_foundation_attributes for All Values

**User asks:** "Show me all foundation settings"

**Correct approach:**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308"
}
```

**Response:** Complete hash of all 40+ parameters

## Common Mistakes - AVOID THESE

### ❌ MISTAKE 1: Trying to Create Foundation with execute_ruby

**NEVER do this:**
```ruby
# Creating foundation geometry manually
entities.add_face(points)
face.pushpull(depth)
```

**Why wrong:**
- No Medeek integration
- No engineering parameters
- Missing footing, rebar, anchor bolts
- Not code-compliant

**DO THIS INSTEAD:**
```
Use create_foundation tool
```

### ❌ MISTAKE 2: Calling create_foundation Multiple Times

**NEVER do this:**
```
Step 1: create_foundation(points, depth=24)
Step 2: create_foundation(points, depth=30)  ← Creates SECOND foundation!
```

**DO THIS INSTEAD:**
```
Call create_foundation ONCE with depth=30
```

### ❌ MISTAKE 3: Trying to Modify Before Creation

**NEVER do this:**
```
Step 1: sog_set_attribute('FDEPTH', 30)  ← No foundation exists yet!
Step 2: sog_draw(points)
```

**DO THIS INSTEAD:**
```
Use create_foundation tool - it handles the workflow automatically
```

## Parameter Reference

### Basic Parameters (Always Available)

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| outline_points | Corner points of foundation | REQUIRED | [x,y,z] arrays |
| foundation_depth | Total depth (slab top to footing bottom) | 24 | inches |
| slab_thickness | Concrete slab thickness | 4 | inches |
| footing_width | Footing width | 16 | inches |

### Optional: Garage Curb

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| garage_curb | Enable garage door curb | false | boolean |
| curb_width | Curb width | 4 | inches |
| curb_height | Curb height | 4 | inches |

### Optional: Rebar Reinforcement

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| rebar_enabled | Enable rebar options | false | boolean |
| top_bar_enabled | Top footing bars | false | boolean |
| top_bar_diameter | Top bar diameter | 0.5 | inches (#4) |
| top_bar_quantity | Number of top bars | 2 | integer (1, 2, or 3) |
| bottom_bar_enabled | Bottom footing bars | false | boolean |
| bottom_bar_diameter | Bottom bar diameter | 0.5 | inches (#4) |
| bottom_bar_quantity | Number of bottom bars | 2 | integer (1, 2, or 3) |
| slab_reinforcement_enabled | Slab reinforcement | false | boolean |
| slab_reinforcement_type | Reinforcement type | "6X6-W1.4XW1.4" | string (see valid values below) |
| slab_reinforcement_spacing | Reinforcement spacing | 12 | inches |

**Valid slab_reinforcement_type values:**
- Wire mesh: `"6X6-W1.4XW1.4"`, `"6X6-W2.9XW2.9"`
- Bar: `"#3-BAR"`, `"#4-BAR"`, `"#5-BAR"`, `"#6-BAR"`, `"#7-BAR"`, `"#8-BAR"`, `"#9-BAR"`, `"#10-BAR"`, `"#11-BAR"`, `"#14-BAR"`, `"#18-BAR"`

### Optional: Anchor Bolts

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| anchor_bolts_enabled | Enable anchor bolts | false   | boolean |
| bolt_size | Bolt length | "12"    | string ("10", "12", "14") |
| bolt_diameter | Bolt diameter | "1/2"   | string ("1/2", "5/8") |
| washer_type | Washer size | "2x2"   | string ("2x2", "3x3") |
| bolt_spacing_ft | Bolt spacing | 6.0     | float (feet OC) |
| sill_width | Sill plate width | 5.5     | float (inches, 2x4) |
| sill_thickness | Sill plate thickness | 1.5     | float (inches, 2x4) |
| corner_distance | Distance from corner | 12.0    | float (inches) |

### Optional: FPSF Insulation

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| fpsf_enabled | Enable Frost Protected Shallow Foundation insulation | false | boolean |
| insulation_type | Insulation configuration type | "None" | string (see valid values below) |
| vertical_insulation | Vertical insulation R-value | 2.0 | float (R-value) |
| wing_insulation | Horizontal wing insulation R-value | 2.0 | float (R-value) |
| corner_insulation | Corner insulation R-value | 2.0 | float (R-value) |
| dim_a | FPSF dimension A | 24.0 | inches |
| dim_b | FPSF dimension B | 24.0 | inches |
| dim_c | FPSF dimension C | 24.0 | inches |

**Valid insulation_type values:**
- `"Vertical Only"` - Vertical perimeter insulation only
- `"Vert. and Horz."` - Vertical and horizontal wing insulation
- `"None"` - No FPSF insulation

### Optional: Slab Insulation

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| slab_insulation_enabled | Enable slab insulation | false | boolean |
| slab_insulation | Slab insulation R-value | 2.0 | float (R-value) |

### Optional: Subbase

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| subbase_enabled | Enable subbase layer beneath slab | false | boolean |
| subbase_depth | Subbase layer depth | 4.0 | inches |
| subbase_material | Subbase material type | "Gravel" | string (see valid values below) |

**Valid subbase_material values:**
- `"Gravel"` - Gravel fill
- `"Stone1"` - Crushed stone
- `"corrugated_metal"` - Corrugated metal (vapor barrier)

### Optional: Perimeter Drain

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| drain_enabled | Enable perimeter drainage system | false | boolean |

## Examples

### Example 1: Simple 40' × 60' Slab with 30" Footer

**User request:** "Create a 40' × 60' concrete slab with a 30" deep footer"

**Step 1: Create foundation (geometry only)**
```json
{
  "outline_points": [[0, 0, 0], [480, 0, 0], [480, 720, 0], [0, 720, 0]]
}
```

**Response:**
```json
{
  "status": "created",
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500"
}
```

**Step 2: Modify foundation (set footer depth)**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500",
  "foundation_depth": 30
}
```

**Result:** 40' × 60' slab with 30" footer depth

### Example 2: Foundation with Rebar and Anchor Bolts

**User request:** "Create a 30' × 40' slab with rebar and anchor bolts"

**Step 1: Create foundation (geometry only)**
```json
{
  "outline_points": [[0,0,0], [360,0,0], [360,480,0], [0,480,0]]
}
```

**Response:**
```json
{
  "status": "created",
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091600"
}
```

**Step 2: Modify foundation (add rebar and anchor bolts)**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091600",
  "rebar_enabled": true,
  "bottom_bar_enabled": true,
  "bottom_bar_diameter": 0.5,
  "bottom_bar_quantity": 2,
  "slab_reinforcement_enabled": true,
  "slab_reinforcement_type": "WWF",
  "anchor_bolts_enabled": true,
  "bolt_size": "12",
  "bolt_diameter": "1/2",
  "bolt_spacing_ft": 6.0
}
```

**Result:** 30' × 40' slab with rebar reinforcement and anchor bolts

### Example 3: Modifying an Existing Foundation

**User request:** "Change that foundation to 36 inches deep and add anchor bolts"

**Step 1: Get foundation group_name** (from previous create_foundation response or by asking the user)
```
group_name: "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500"
```

**Step 2: Call modify_foundation**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260408091500",
  "foundation_depth": 36,
  "anchor_bolts_enabled": true,
  "bolt_size": "14",
  "bolt_diameter": "5/8",
  "bolt_spacing_ft": 6.0
}
```

**Result:** Existing foundation is modified - depth changed to 36", anchor bolts added. All other parameters (slab thickness, footing width, etc.) remain unchanged.

**DO NOT delete and recreate the foundation!**

### Example 4: Reading Foundation Settings

**User request:** "What's the depth of this foundation?"

**Step 1: Get foundation name from create_foundation response**
```json
{
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308"
}
```

**Step 2: Read specific attribute**
```json
{
  "attribute_name": "FDEPTH",
  "group_name": "FOUNDATION_SOG_POLYGON_ASSEMBLY_20260315133308"
}
```

**Response:** `24.0` (inches)

## Summary - Key Rules

### Creating New Foundations - TWO STEP WORKFLOW
1. ✅ **Step 1: Call create_foundation with ONLY outline_points** (geometry)
2. ✅ **Step 2: Call modify_foundation with ALL custom parameters** (depth, rebar, bolts, etc.)
3. ❌ **NEVER pass parameters to create_foundation** - only outline_points allowed
4. ❌ **NEVER call create_foundation multiple times** - this creates MULTIPLE foundations

### Modifying Existing Foundations
5. ✅ **Use modify_foundation** to change parameters on existing foundations
6. ✅ **Combine all changes in ONE modify_foundation call** - don't make multiple calls
7. ✅ **Only provide the parameters you want to CHANGE** - others remain unchanged
8. ❌ **NEVER delete and recreate** to modify a foundation - use modify_foundation instead

### Reading Foundation Data
9. ✅ **Use read_foundation_attributes** to get all parameters
10. ✅ **Use read_foundation_attribute** to query single values

### General Rules
11. ❌ **NEVER use execute_ruby** to create foundations manually - use create_foundation + modify_foundation
12. ❌ **NEVER pass parameters other than outline_points to create_foundation**

## Need Help?

- See Medeek Foundation API docs: https://design.medeek.com/resources/medeek_foundation_api.html
- See attribute index: https://design.medeek.com/resources/medeek_sog_attribute_index.html
