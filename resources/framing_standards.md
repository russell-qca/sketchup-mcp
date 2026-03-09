# Standard Framing Practices

## Wall Framing

### Stud Spacing
- **Standard**: 16 inches on center (OC)
- **Economy**: 24 inches OC (for single-story, non-load-bearing)
- **Corners**: Always doubled or tripled studs
- **Door/window openings**: King studs + jack studs (trimmers)

### Standard Wall Heights
- **Residential**: 8 feet (96 inches) - most common
- **Higher ceiling**: 9 feet (108 inches)
- **Commercial**: 10 feet (120 inches) or higher

### Lumber Sizes (Actual Dimensions)
- **2x4**: 1.5" × 3.5" - standard wall studs
- **2x6**: 1.5" × 5.5" - exterior walls (better insulation)
- **2x8**: 1.5" × 7.25" - headers over openings
- **2x10**: 1.5" × 9.25" - larger headers
- **2x12**: 1.5" × 11.25" - floor joists, larger headers

### Wall Components
- **Bottom plate**: 2x4 or 2x6 (horizontal, on floor)
- **Top plate**: Double 2x4 or 2x6 (two horizontal members)
- **Studs**: 2x4 or 2x6 vertical members at 16" or 24" OC
- **Cripple studs**: Short studs above/below openings
- **Jack studs (trimmers)**: Support header at openings
- **King studs**: Full-height studs flanking openings
- **Header**: Beam over door/window openings

## Floor Framing

### Joist Spacing
- **Standard**: 16 inches OC
- **Stronger floors**: 12 inches OC
- **Engineered joists**: May allow 24 inches OC

### Common Joist Sizes by Span
- **2x6**: Up to 9 feet
- **2x8**: Up to 12 feet
- **2x10**: Up to 16 feet
- **2x12**: Up to 20 feet
- (These are general guidelines; actual spans depend on species, grade, and loads)

### Floor Components
- **Sill plate**: 2x4 or 2x6 (on foundation, treated lumber)
- **Rim joist (band)**: 2x8, 2x10, or 2x12 (perimeter)
- **Floor joists**: 2x8, 2x10, or 2x12 at 16" OC
- **Bridging/blocking**: Cross-bracing between joists at mid-span
- **Subfloor**: 3/4" plywood or OSB

## Headers

### Header Sizing for Openings
Headers carry the load above an opening (door, window) down to jack studs.

| Opening Width | Header Size | Notes |
|--------------|-------------|-------|
| Up to 3'     | 2x6         | Non-load-bearing |
| 3' to 5'     | 2x8         | Standard door |
| 5' to 7'     | 2x10        | Standard window or wide door |
| 7' to 9'     | 2x12        | Large opening |
| 9' to 12'    | Double 2x12 or LVL | Engineered beam |
| Over 12'     | Engineered beam | Consult engineer |

### Header Construction
- **Double header**: Two 2x members with 1/2" spacer
- **Total thickness**: 3" (matches 2x4 wall with 1/2" spacer)
- **For 2x6 walls**: Use 2x headers with 2.5" spacer or triple 2x

## Opening Framing

### Door Frame
- **Rough opening width**: Door width + 2 inches (for frame/shims)
- **Rough opening height**: Door height + 2.5 inches
- **Standard interior door**: 30", 32", or 36" wide × 80" tall
- **Standard exterior door**: 36" wide × 80" tall
- **Jack studs**: Two per side (support header)
- **King studs**: Two per side (full height)
- **Header**: Sized per table above
- **Cripple studs above**: At regular spacing (16" OC)

### Window Frame
- **Rough opening**: Window unit size + 1/2" to 1" per side
- **Sill**: 2x4 or 2x6 horizontal at bottom of opening
- **Jack studs**: Support header and sill
- **King studs**: Full height
- **Cripple studs**: Above and below opening at regular spacing

## SketchUp Best Practices

### Modeling Approach
1. **Use actual lumber dimensions**: Not nominal sizes
2. **Model from bottom up**: Foundation → floor → walls → roof
3. **Work in inches**: SketchUp's default unit
4. **Use components**: Make repetitive elements (studs) components
5. **Layer organization**: Floor frame, walls, roof separate layers
6. **Snap to grid**: Use 1" or 16" grid for accurate spacing

### Component Strategy
- **Create master components**: Single stud, joist, etc.
- **Use copy arrays**: For spacing studs/joists
- **Name clearly**: "2x4_Stud_92.625in" (92.625" = 96" - 3.375" for plates)
- **Group assemblies**: Group entire wall frames

### Typical Wall Assembly
1. Draw bottom plate (1.5" × 3.5" × wall length)
2. Draw double top plate (two 1.5" × 3.5" × wall length)
3. Create single stud component (1.5" × 3.5" × 92.625")
4. Copy stud at 16" OC (or 24" OC)
5. Frame openings with jack/king studs and headers
6. Add cripple studs above/below openings
7. Make entire wall a group or component

### Measurement Tips
- **Stud length for 8' wall**: 92.625" (96" - 3.375" for 3 plates)
- **16" OC means**: 16" from center of one stud to center of next
- **Start corner stud at 0**: Next stud at 16", then 32", 48", etc.
- **At openings**: Maintain regular spacing where possible

## Code Requirements (General US)

### Minimum Standards
- **Stud spacing**: Maximum 24" OC
- **Top plate**: Must be doubled
- **Corner bracing**: Required (let-in bracing, structural sheathing, or metal straps)
- **Connections**: Studs to plates: 2 nails per connection (16d)
- **Headers**: Must be properly sized for span and load
- **Fire blocking**: Required at 10' vertical intervals in walls
- **Treated lumber**: Required for sill plates on concrete

### Nailing Schedule (Typical)
- **Stud to plate**: 2 × 16d nails (end nailing)
- **Top plate overlap**: 16d nails at 16" OC
- **Rim joist to sill**: 16d at 16" OC
- **Joist to sill/rim**: 3 × 16d (toe nailing)
- **Subfloor to joists**: 8d at 6" OC edges, 12" OC field

## Common Mistakes

1. **Using nominal dimensions**: Always use actual lumber sizes in model
2. **Forgetting double top plate**: Two top plates required by code
3. **Wrong stud length**: Must account for plate thickness
4. **Inconsistent spacing**: Maintain 16" or 24" OC throughout
5. **Undersized headers**: Check span tables for proper sizing
6. **Missing jack studs**: Required to support header
7. **No corner studs**: Corners need structural support
8. **Ignoring window/door rough openings**: Must be correct for unit installation

## Quick Reference Dimensions

| Element | Size | Spacing/Height |
|---------|------|----------------|
| Wall studs | 2x4 or 2x6 | 16" or 24" OC |
| Stud length (8' wall) | 92.625" | - |
| Bottom plate | 2x4 or 2x6 | Continuous |
| Top plate | 2x4 or 2x6 (doubled) | Continuous |
| Floor joists | 2x8, 2x10, 2x12 | 16" OC |
| Rim joist | Same as joists | Perimeter |
| Door rough opening | Door + 2" width, + 2.5" height | - |
| Window rough opening | Window + 0.5-1" per side | - |
