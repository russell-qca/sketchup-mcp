# Roof Truss Implementation Guide
## Production-Quality Geometry for King Post and Fink Trusses

---

## Overview

This implementation creates accurate roof trusses with proper engineering geometry. The code implements fundamental truss principles with absolute reference points that ensure structural accuracy and proper member connections.

**Supported Types:**
- **King Post Truss**: 4 members (BC, 2 TC, 1 king post) - spans up to 26'
- **Fink Truss (W-Truss)**: 7 members (BC, 2 TC, 4 webs) - spans 20-60'

---

## Fundamental Principles

### 1. Absolute Reference Points (DO NOT CHANGE)

These reference points are the foundation of all truss geometry and **MUST NEVER BE MODIFIED**:

#### Heel Joints
```
Left heel:  (origin.x, origin.z)
Right heel: (origin.x + span, origin.z)
```
- These are where the bottom corners of the bottom chord meet the bottom edges of the top chords
- The heel joint intersection is **FIXED** regardless of overhang or other parameters
- All overhang calculations extend BEYOND these fixed points

#### Apex Height
```
peak_x = origin.x + (span / 2)
peak_z = origin.z + rise_to_peak
```
- Measured from the **BOTTOM** of the bottom chord
- For 24' span, 6:12 pitch: `rise = 72"`, so `peak_z = origin.z + 72"`
- This is where the centerline at the apex intersects with the bottom of the bottom chord

#### Rise Calculation
```
run_to_peak = span / 2
rise_to_peak = (run_to_peak / pitch_run) × pitch_rise

Example: 24' span, 6:12 pitch
run_to_peak = 288 / 2 = 144"
rise_to_peak = (144 / 12) × 6 = 72"
```

---

## Member Geometry

### Bottom Chord

**Length**: Exactly `span` (no overhang)

**Geometry**:
- Horizontal member from `(origin.x, origin.z)` to `(origin.x + span, origin.z)`
- Cross-section: `lumber_width × lumber_depth` (1.5" × 3.5" for 2x4)
- Angled cuts at ends matching roof pitch for proper heel joint

**Angled End Cuts**:
```ruby
cut_horizontal = lumber_depth × (run / rise)

# For 6:12 pitch, 2x4 lumber:
cut_horizontal = 3.5 × (12 / 6) = 7.0"
```

**Profile Points** (Y=0 plane, before extrusion):
```ruby
[
  (bc_start_x, 0, origin.z),                    # Bottom-left corner
  (bc_end_x, 0, origin.z),                      # Bottom-right corner
  (bc_end_x - cut_horizontal, 0, bc_top_z),    # Top-right (cut inward)
  (bc_start_x + cut_horizontal, 0, bc_top_z)   # Top-left (cut inward)
]
```

### Top Chords

**Slope**: From heel joint to apex, following roof pitch

**Absolute Requirements**:
- Bottom edge MUST pass through heel joint at `(origin.x, origin.z)` or `(origin.x + span, origin.z)`
- Bottom edge MUST pass through apex at `(peak_x, peak_z)`

**With Overhang**:
- Extends beyond heel joint by `overhang` distance (horizontally measured)
- Outer edge drops according to pitch: `(overhang / run) × rise`
- Vertical cut at outer edge (normal to span)

**Left Top Chord Geometry**:
```ruby
# Calculate slope
left_dx = peak_x - heel_left_x
left_dz = peak_z - heel_left_z
left_angle = Math.atan2(left_dz, left_dx)
left_offset_z = lumber_depth * Math.cos(left_angle)

# Outer edge (with overhang)
tc_left_outer_x = heel_left_x - overhang
tc_left_outer_z = heel_left_z - (overhang / run) × rise

# Four corners (trapezoidal profile with vertical cuts at both ends)
bottom_left:  (tc_left_outer_x, 0, tc_left_outer_z)
top_left:     (tc_left_outer_x, 0, tc_left_outer_z + lumber_depth / cos(angle))
top_right:    (peak_x, 0, peak_z + left_offset_z)
bottom_right: (peak_x, 0, peak_z)
```

**Right Top Chord**: Mirror of left, extending to the right

**Key Formula - Vertical Cut Height**:
```ruby
vertical_height = lumber_depth / Math.cos(angle)

# For 6:12 pitch (26.57°), 2x4 lumber:
vertical_height = 3.5 / cos(26.57°) = 3.91"
```

### King Post

**Position**: Vertical member at center, from BC top to apex

**Geometry**:
- Bottom: `bc_top_z` (top surface of bottom chord)
- Top: Peaked with angled cuts matching TC slope

**Peaked Top**:
```ruby
half_depth = lumber_depth / 2.0
kp_top_drop = half_depth × (rise / run)

# Five corners (pentagonal profile)
bottom_left:  (kp_left, 0, bc_top_z)
bottom_right: (kp_right, 0, bc_top_z)
top_right:    (kp_right, 0, peak_z - kp_top_drop)
peak:         (peak_x, 0, peak_z)
top_left:     (kp_left, 0, peak_z - kp_top_drop)
```

This creates angled cuts parallel to the bottom edges of the top chords, eliminating overlap.

---

## Overhang Implementation

**Key Principle**: Only top chords extend for overhang. Bottom chord stays at exactly `span` length.

**Measurement**: Overhang is measured **horizontally** from the heel joint to the outer edge of the top chord.

**Typical Values**: 12-24 inches (12" is common for residential)

**Geometry**:
```ruby
# Outer edge position
outer_x = heel_x ± overhang  # (+) for right side, (-) for left side
outer_z = heel_z - (overhang / run) × rise

# The top chord bottom edge drops according to pitch as it extends
```

**With overhang = 0**: Top chord ends at heel joint with no extension beyond walls

**With overhang = 12"**: Top chord extends 12" horizontally beyond heel joint

---

## Coordinate System

### Y-Axis (Extrusion Direction)
All members exist from **Y = -lumber_width to Y = 0**:
- Profiles created at Y=0 plane
- Extruded in **negative Y direction**: `pushpull(-lumber_width)`
- For 2x4 lumber: Y = -1.5" to Y = 0

### X-Axis (Span Direction)
- Origin at left wall: `origin.x`
- Right wall at: `origin.x + span`
- Overhang extends beyond: `origin.x - overhang` to `origin.x + span + overhang`

### Z-Axis (Vertical)
- Base of bottom chord: `origin.z`
- Top of bottom chord: `origin.z + lumber_depth` (= `bc_top_z`)
- Apex: `origin.z + rise_to_peak`

---

## Implementation Details

### Function Signatures

```ruby
def self.create_king_post_truss_accurate(span, rise, run, overhang, origin, lumber_width, lumber_depth)
  # span: clear span in inches (wall-to-wall)
  # rise: pitch rise value (e.g., 6 for 6:12)
  # run: pitch run value (e.g., 12 for 6:12)
  # overhang: horizontal extension in inches (0 for no overhang)
  # origin: Geom::Point3d for left wall base position
  # lumber_width: 1.5" for 2x4
  # lumber_depth: 3.5" for 2x4
end
```

### Member Creation Order
1. Bottom chord (with angled end cuts)
2. Left top chord (with overhang and vertical cuts)
3. Right top chord (with overhang and vertical cuts)
4. King post (with peaked top) OR web members (for Fink)

### Helper Functions

**`create_lumber_member_sloped()`**:
- Creates sloped lumber members with perpendicular lumber depth
- Supports `trim_start` and `trim_end` for vertical cuts at ends
- Used for older implementation; current code uses manual geometry

---

## Design Rules

### DO NOT CHANGE
1. **Heel joint positions**: `(origin.x, origin.z)` and `(origin.x + span, origin.z)`
2. **Apex height formula**: `origin.z + rise_to_peak`
3. **Bottom chord length**: Exactly `span`
4. **Y-plane consistency**: All members from Y=-lumber_width to Y=0

### ALWAYS DO
1. **Measure apex from BC bottom**: Not from top of BC
2. **Extend overhang from heel joint**: Heel joint stays fixed
3. **Add vertical cuts at TC ends**: Normal to span direction
4. **Peak king post top**: Angled cuts matching TC slope

### PARAMETERS
- `overhang`: Default 12" (can be 0 for no overhang)
- `lumber_width`: Default 1.5" (2x4 actual width)
- `lumber_depth`: Default 3.5" (2x4 actual depth, or 5.5" for 2x6)
- `pitch`: Typical 6:12 (can be 4:12 to 12:12)

---

## Validation Test Case

**Input**: 24' span, 6:12 pitch, 12" overhang, 2x4 lumber

**Expected Dimensions**:
```
span = 288"
run_to_peak = 144"
rise_to_peak = 72"

Heel joints (ABSOLUTE):
  Left:  (origin.x, origin.z)
  Right: (origin.x + 288", origin.z)

Apex: (origin.x + 144", origin.z + 72")

Bottom chord:
  Length: 288" (exact)
  Angled cuts: 7.0" horizontal

Top chords:
  Outer edges: origin.x ± 12", drop 6" from heel
  Vertical cuts at outer edges and apex
  Bottom edge passes through heel joints and apex

King post:
  Bottom: bc_top_z = origin.z + 3.5"
  Peak: origin.z + 72"
  Top drops: 1.75" × (6/12) = 0.875" on each side
```

---

## Common Pitches

| Pitch | Angle | Rise/Run | Use Case |
|-------|-------|----------|----------|
| 4:12  | 18.43° | 0.333 | Low slope, modern |
| 6:12  | 26.57° | 0.500 | Most common residential |
| 8:12  | 33.69° | 0.667 | Steeper residential |
| 12:12 | 45.00° | 1.000 | Very steep, mountain |

---

## Code Location

**Main Implementation**: `/sketchup_plugin/sketchup_mcp_server.rb`
- `create_king_post_truss_accurate()` - Lines ~642-778
- `create_fink_truss_accurate()` - Lines ~780+

**Helper Functions**: Same file, lines ~570-640

---

## Future Enhancements

### Fink Truss Web Members
Currently implemented with basic W-pattern. Panel points at thirds of span for standard residential configuration.

### Potential Additions
- Queen post trusses
- Scissor trusses (vaulted ceiling)
- Attic trusses (habitable space)
- Gusset plate geometry
- Engineering load calculations

---

## Changelog

**2026-03-07**: Current implementation
- ✅ Absolute heel joint reference points
- ✅ Apex measured from BC bottom
- ✅ Overhang extends top chords only
- ✅ Vertical cuts at TC ends
- ✅ Peaked king post top
- ✅ Y-plane consistency (Y=-lumber_width to Y=0)
- ✅ Angled cuts on BC ends

---

**Status**: Production Ready
**Author**: Systematically refined implementation
**Last Updated**: March 7, 2026
