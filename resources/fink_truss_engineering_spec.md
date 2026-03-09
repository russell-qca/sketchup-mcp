# Fink Truss Engineering Specification
## Formal Geometry Definition

---

## 1. Overview

A **Fink truss** (also called W-truss) is the most common residential roof truss design. It consists of:
- 1 Bottom Chord (BC)
- 2 Top Chords (TC left and right)
- 4 Web members forming a W-pattern

## 2. Coordinate System

All dimensions in inches.

**Reference Points:**
- Origin (0, 0, 0) = Left wall interior, at base of bottom chord
- X-axis: horizontal, left to right
- Y-axis: perpendicular to truss (for extrusion)
- Z-axis: vertical height

**Key Reference Plane:**
- `bc_top_z` = Top surface of bottom chord = origin.z + lumber_depth
- All member connections reference this plane

## 3. Given Parameters

- `span` = Clear span in inches (wall-to-wall, e.g., 288" for 24')
- `pitch` = Rise:run ratio (e.g., 6:12 means 6" rise per 12" run)
- `overhang` = Extension beyond walls in inches (typically 12-24")
- `lumber_width` = 1.5" (actual 2x dimension)
- `lumber_depth` = 3.5" for 2x4, 5.5" for 2x6, etc.

## 4. Calculated Dimensions

```
run_to_peak = span / 2
rise_to_peak = (run_to_peak / pitch_run) × pitch_rise

For 24' span, 6:12 pitch:
run_to_peak = 288 / 2 = 144"
rise_to_peak = (144 / 12) × 6 = 72"
```

## 5. Member Definitions

### 5.1 Bottom Chord (BC)

**Geometry:** Horizontal rectangular member

**Endpoints:**
- Start: `(-overhang, 0, 0)`
- End: `(span + overhang, 0, 0)`

**Cross-section:**
- Base at z = 0
- Top at z = lumber_depth

**Profile points (before extrusion):**
```
P1: (-overhang, 0, 0)
P2: (span + overhang, 0, 0)
P3: (span + overhang, 0, lumber_depth)
P4: (-overhang, 0, lumber_depth)
```

Extrude -lumber_width in Y direction.

### 5.2 Top Chords (TC)

**Left Top Chord:**
- Start (heel): `(-overhang, 0, heel_z)`
- End (peak): `(run_to_peak, 0, peak_z)`

**Right Top Chord:**
- Start (peak): `(run_to_peak, 0, peak_z)`
- End (heel): `(span + overhang, 0, heel_z)`

**Z-coordinates:**
```
heel_z = bc_top_z - (overhang / pitch_run) × pitch_rise
peak_z = bc_top_z + rise_to_peak

For 24' span, 6:12 pitch, 12" overhang:
bc_top_z = 3.5"
heel_z = 3.5 - (12/12) × 6 = 3.5 - 6 = -2.5"
peak_z = 3.5 + 72 = 75.5"
```

**Note:** Top chords are sloped members created with perpendicular lumber depth offset.

### 5.3 Web Members - Fink Pattern

The Fink W-pattern uses **panel points** on the bottom chord where webs connect.

#### Panel Point Definition

For standard residential Fink truss, divide the span into 3 equal panels:

```
panel_width = span / 3

Left panel point:
panel_1_x = 0 + panel_width = span / 3

Right panel point:
panel_2_x = 0 + 2 × panel_width = 2 × span / 3

For 24' span:
panel_1_x = 288 / 3 = 96"
panel_2_x = 288 × 2/3 = 192"
```

#### 5.3.1 Strut Web Left (SWL)

**Function:** Compression member from BC to TC, outer web of W

**Bottom endpoint:** Panel point 1 on BC top
```
Bottom: (panel_1_x, 0, bc_top_z)
```

**Top endpoint:** Point on left top chord

The top connection is at a point along the TC. For standard Fink, this is typically at **60% of the distance from heel to peak**:

```
tc_connection_ratio = 0.6
tc_point_x = heel_left_x + (peak_x - heel_left_x) × tc_connection_ratio
tc_point_z = heel_left_z + (peak_z - heel_left_z) × tc_connection_ratio

For 24' span, 6:12 pitch:
heel_left_x = -12"
peak_x = 144"
tc_point_x = -12 + (144 - (-12)) × 0.6 = -12 + 156 × 0.6 = -12 + 93.6 = 81.6"
tc_point_z = -2.5 + (75.5 - (-2.5)) × 0.6 = -2.5 + 78 × 0.6 = -2.5 + 46.8 = 44.3"

Top: (81.6", 0, 44.3")
```

#### 5.3.2 Center Web Left (CWL)

**Function:** Tension member from BC to peak, inner web of W

**Bottom endpoint:** Same panel point 1 on BC top
```
Bottom: (panel_1_x, 0, bc_top_z)
```

**Top endpoint:** Peak
```
Top: (run_to_peak, 0, peak_z)

For 24' span:
Top: (144", 0, 75.5")
```

#### 5.3.3 Strut Web Right (SWR)

**Function:** Mirror of SWL on right side

**Bottom endpoint:** Panel point 2 on BC top
```
Bottom: (panel_2_x, 0, bc_top_z)
```

**Top endpoint:** Point on right top chord at 60% from peak to right heel
```
tc_connection_ratio = 0.6
tc_point_x = peak_x + (heel_right_x - peak_x) × tc_connection_ratio
tc_point_z = peak_z + (heel_right_z - peak_z) × tc_connection_ratio

For 24' span, 6:12 pitch:
heel_right_x = 300"
peak_x = 144"
tc_point_x = 144 + (300 - 144) × 0.6 = 144 + 156 × 0.6 = 144 + 93.6 = 237.6"
tc_point_z = 75.5 + (-2.5 - 75.5) × 0.6 = 75.5 + (-78) × 0.6 = 75.5 - 46.8 = 28.7"

Top: (237.6", 0, 28.7")
```

#### 5.3.4 Center Web Right (CWR)

**Function:** Mirror of CWL on right side

**Bottom endpoint:** Same panel point 2 on BC top
```
Bottom: (panel_2_x, 0, bc_top_z)
```

**Top endpoint:** Peak
```
Top: (run_to_peak, 0, peak_z)

For 24' span:
Top: (144", 0, 75.5")
```

## 6. Visual Representation

```
For 24' span, 6:12 pitch, 12" overhang:

             Peak (144, 75.5)
                  /\
                 /  \
                / TC \
               /  |   \
              /   |    \
             / CW | CW  \
            /   \ | /    \
           / SW  \|/ SW   \
          /    X     X     \
         /    /       \     \
    Heel/____/__________\____\Heel
   (-12)   96          192   (300)
           P1           P2

BC Top at Z = 3.5"
Heels at Z = -2.5"
Peak at Z = 75.5"
```

## 7. W-Pattern Explanation

The W-pattern forms because:
1. SWL and CWL both start at panel point P1 (96"), forming a V going up
2. CWL goes to peak (144")
3. SWL goes to TC at 60% point (~82")
4. SWR and CWR both start at panel point P2 (192"), forming a V going up
5. CWR goes to peak (144")
6. SWR goes to TC at 60% point (~238")

**The two V's with their tips at the peak form the W shape.**

## 8. Implementation Notes

### Helper Function Requirements

1. **create_lumber_member_sloped()**
   - Must create member with lumber_depth perpendicular to slope
   - Must handle arbitrary start and end points
   - Returns a face that can be extruded

2. **Connection Points**
   - All webs connect at bc_top_z (not at base)
   - TC connections calculated along the slope line
   - No arbitrary offsets

### Critical Formulas

**Point on a line:**
```ruby
# To find point at ratio t along line from A to B:
point_x = a_x + (b_x - a_x) * t
point_z = a_z + (b_z - a_z) * t
```

**Panel points (thirds):**
```ruby
panel_1_x = origin.x + (span / 3.0)
panel_2_x = origin.x + (2.0 * span / 3.0)
```

**TC connection point (at 60% from heel to peak):**
```ruby
tc_ratio = 0.6
tc_x = heel_x + (peak_x - heel_x) * tc_ratio
tc_z = heel_z + (peak_z - heel_z) * tc_ratio
```

## 9. Validation Test Case

**Input:**
- Span: 24' (288")
- Pitch: 6:12
- Overhang: 12"
- Lumber: 2x4 (1.5" × 3.5")

**Expected Coordinates:**

| Member | Bottom/Start | Top/End |
|--------|-------------|---------|
| BC | (-12, 0, 0) | (300, 0, 0) |
| TCL | (-12, 0, -2.5) | (144, 0, 75.5) |
| TCR | (144, 0, 75.5) | (300, 0, -2.5) |
| SWL | (96, 0, 3.5) | (81.6, 0, 44.3) |
| CWL | (96, 0, 3.5) | (144, 0, 75.5) |
| SWR | (192, 0, 3.5) | (237.6, 0, 28.7) |
| CWR | (192, 0, 3.5) | (144, 0, 75.5) |

**Expected Measurements:**
- BC length: 312"
- TC length (each): ~161" (√((156)² + (78)²))
- Peak height above base: 75.5"
- Clear W-pattern visible

## 10. Alternative Panel Configurations

If thirds don't look right, alternative panel ratios:

### Configuration A: Quarter Points (More Open W)
```ruby
panel_1_x = origin.x + (span / 4.0)
panel_2_x = origin.x + (3.0 * span / 4.0)
```

### Configuration B: 40-60 Split (Tighter W)
```ruby
panel_1_x = origin.x + (span * 0.4)
panel_2_x = origin.x + (span * 0.6)
```

**Recommended:** Start with thirds (Configuration as specified above). This is most common for residential trusses.

---

**Status:** Ready for Implementation
**Date:** 2026-03-06
**Validation Required:** Yes - test with 24' span, 6:12 pitch first
