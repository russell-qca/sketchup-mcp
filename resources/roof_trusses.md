# Roof Truss Design Guide

## Overview
Roof trusses are engineered structural frameworks that support roof loads and transfer weight to exterior walls. They are more efficient than traditional rafter framing for most residential and commercial applications.

## Standard Truss Types

### King Post Truss
- **Description**: Simplest truss design with single central vertical post
- **Span**: Up to 26 feet
- **Use**: Small residential buildings, garages, sheds
- **Components**:
  - Top chords (2): Form the roof slope
  - Bottom chord (1): Horizontal member spanning the width
  - King post (1): Central vertical support
  - Web members (2): Diagonal braces from peak to bottom chord ends

### Queen Post Truss
- **Description**: Two vertical posts instead of one central post
- **Span**: 26-32 feet
- **Use**: Medium residential buildings
- **Components**:
  - Top chords (2): Form the roof slope
  - Bottom chord (1): Horizontal spanning member
  - Queen posts (2): Vertical supports positioned symmetrically
  - Web members (4): Diagonal braces

### Fink Truss (W-Truss)
- **Description**: Most common residential truss, creates W-pattern with web members
- **Span**: 20-60 feet (most efficient)
- **Use**: Standard residential construction, most versatile
- **Components**:
  - Top chords (2): Form the roof slope
  - Bottom chord (1): Horizontal spanning member
  - Web members (4+): Form W or double-W pattern for load distribution

## Standard Dimensions

### Member Sizes
- **Top chord**: 2x4 or 2x6 lumber (2x6 for spans over 30')
- **Bottom chord**: 2x4 or 2x6 lumber
- **Web members**: 2x4 lumber
- **Actual dimensions**: 2x4 = 1.5" x 3.5", 2x6 = 1.5" x 5.5"

### Spacing
- **Standard spacing**: 24 inches on center (OC)
- **Heavy loads**: 16 inches OC
- **Light loads**: 32 inches OC

### Common Roof Pitches
- **4:12 pitch**: 4 inches rise per 12 inches run (18.43°)
- **6:12 pitch**: 6 inches rise per 12 inches run (26.57°) - most common
- **8:12 pitch**: 8 inches rise per 12 inches run (33.69°)
- **12:12 pitch**: 12 inches rise per 12 inches run (45°) - steep roof

## SketchUp Implementation Guidelines

### Creating Trusses
1. **Work in inches**: SketchUp's default unit
2. **Create as component**: Make first truss a component for easy duplication
3. **Use precise measurements**: Trusses must be identical for proper load distribution
4. **Model actual lumber sizes**: Use 1.5" x 3.5" for 2x4, not nominal 2x4
5. **Position correctly**: Bottom chord typically at ceiling height (8' for residential)

### Best Practices
- **Snap to grid**: Enable length snapping for accurate connections
- **Use guides**: Create guide lines for consistent angles
- **Group by type**: Keep all trusses of same type in same layer
- **Label components**: Name components clearly (e.g., "Fink_Truss_6-12_24ft")
- **Check connections**: Ensure all members meet at proper angles
- **Use copy/array**: Use Move + Ctrl (Win) or Option (Mac) for exact spacing

### Typical Workflow
1. Draw bottom chord horizontally at ceiling height
2. Mark midpoint and create vertical guide for peak
3. Calculate peak height using pitch (e.g., 12' span, 6:12 pitch = 6' height)
4. Draw top chords from ends to peak
5. Add web members using guidelines for proper angles
6. Make all geometry a component
7. Copy component along building length at proper spacing

## Design Considerations

### Load Requirements
- **Dead load**: Weight of roof materials (typically 10-15 psf)
- **Live load**: Snow, maintenance loads (varies by region, 20-50 psf)
- **Wind load**: Varies by location and roof pitch

### Connection Points
- All members should meet at **gusset plates** in real construction
- In SketchUp, ensure all lines intersect at common points
- Typical gusset plate size: 6-12 inches, 1/4" to 3/4" plywood or metal

### Overhang
- Typical overhang: 12-24 inches beyond exterior wall
- Extend top chord beyond support point
- May require additional tail pieces

## Common Mistakes to Avoid
1. **Incorrect lumber sizes**: Using nominal vs actual dimensions
2. **Inconsistent spacing**: Trusses must be evenly spaced
3. **Wrong pitch calculation**: Rise/run must be consistent on both sides
4. **Missing members**: Incomplete web patterns create weak points
5. **Poor connections**: Members not meeting at common points
6. **Ignoring building width**: Truss span must match wall-to-wall distance

## Quick Reference

| Building Width | Recommended Truss Type | Typical Pitch | Spacing |
|---------------|------------------------|---------------|---------|
| Under 20'     | King Post              | 4:12 to 8:12  | 24" OC  |
| 20-26'        | King Post or Fink      | 6:12 to 8:12  | 24" OC  |
| 26-32'        | Fink                   | 6:12 to 8:12  | 24" OC  |
| 32-40'        | Fink (with 2x6)        | 6:12          | 24" OC  |
| 40-60'        | Fink or Custom         | 4:12 to 6:12  | 16" OC  |

## Example Calculations

### 24-foot span building with 6:12 pitch:
- **Half span**: 24' ÷ 2 = 12 feet = 144 inches
- **Rise**: 144" ÷ 12 × 6 = 72 inches = 6 feet
- **Peak height above bottom chord**: 6 feet
- **Top chord length**: √(144² + 72²) = 161.2 inches = 13.43 feet
- **Number of trusses for 30' building**: 30' ÷ 2' = 15 trusses (at 24" OC)
