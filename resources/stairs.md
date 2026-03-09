# Stair Design Standards

## Building Code Requirements (IRC - International Residential Code)

### Critical Dimensions
- **Maximum riser height**: 7.75 inches (7 3/4")
- **Minimum riser height**: 4 inches
- **Minimum tread depth**: 10 inches (measured horizontally)
- **Maximum riser variation**: 3/8 inch between highest and lowest riser
- **Minimum headroom**: 80 inches (6' 8") measured vertically
- **Minimum width**: 36 inches clear (between handrails)

### Handrail Requirements
- **Height**: 34-38 inches above nosing
- **Graspable**: Must be graspable (circular 1.25" to 2" diameter)
- **Required**: One side minimum, both sides for stairs wider than 44"
- **Continuity**: Must be continuous for full length of stairs

### Guard (Railing) Requirements
- **Required when**: Stairs have more than 30" total rise
- **Minimum height**: 36 inches (residential), 42 inches (commercial)
- **Maximum opening**: 4 inches (sphere test)

## Stair Design Formula

### The 2R + T Rule
**2(Riser) + Tread = 24-25 inches** (comfortable stride length)

This is the most important relationship for comfortable stairs.

### Examples of Good Combinations
- **7" rise, 11" tread**: 2(7) + 11 = 25 ✓ comfortable
- **7.5" rise, 10" tread**: 2(7.5) + 10 = 25 ✓ comfortable
- **6.5" rise, 12" tread**: 2(6.5) + 12 = 25 ✓ comfortable
- **8" rise, 9" tread**: 2(8) + 9 = 25 ✓ code legal but steep

### Calculating Stairs

**Given: Total rise (floor to floor height)**

1. **Determine number of risers**:
   - Divide total rise by ideal riser (7-7.5")
   - Round to nearest whole number
   - Must be ≤ 7.75" per code

2. **Calculate actual riser height**:
   - Total rise ÷ number of risers

3. **Calculate tread depth**:
   - Use formula: Tread = 25 - 2(Riser)
   - Must be ≥ 10" per code

4. **Calculate total run**:
   - (Number of risers - 1) × Tread depth
   - Note: Number of treads = Number of risers - 1

**Example: 9 foot (108") floor-to-floor height**
- **Target risers**: 108 ÷ 7.5 = 14.4 → round to 14 risers
- **Actual riser**: 108 ÷ 14 = 7.714" ✓ (under 7.75" max)
- **Tread depth**: 25 - 2(7.714) = 9.57" → use 10" (code minimum)
- **Verify**: 2(7.714) + 10 = 25.43" ✓ comfortable
- **Total run**: 13 treads × 10" = 130" = 10.83 feet

## Common Stair Types

### Straight Run
- **Description**: Single flight, no turns
- **Best for**: Short rises, maximum space efficiency in one direction
- **Minimum space**: Total run + 3' landing
- **Pros**: Simplest to build, easiest to navigate
- **Cons**: Requires long straight space

### L-Shaped (Quarter Turn)
- **Description**: 90° turn with landing
- **Best for**: Corner locations, moderate rises
- **Minimum space**: Varies, typically 10' × 10'
- **Landing**: Minimum 36" × 36" (typically match stair width)
- **Pros**: Fits in corners, breaks up climb
- **Cons**: More complex framing

### U-Shaped (Half Turn / Switchback)
- **Description**: 180° turn with landing
- **Best for**: Maximum rise in minimum linear space
- **Minimum space**: Typically 10' × 8'
- **Landing**: Minimum 36" depth
- **Pros**: Compact, good for tight spaces
- **Cons**: Most complex to frame

### Winder Stairs
- **Description**: Wedge-shaped treads instead of landing
- **Code requirements**: Minimum 10" tread at 12" from narrow end
- **Best for**: Very tight spaces
- **Cons**: Less comfortable, more difficult to navigate

## Stair Components

### Structural
- **Stringers (carriages)**: Main support beams
  - **Minimum**: 3 stringers for stairs over 36" wide
  - **Spacing**: Maximum 18" apart
  - **Size**: Typically 2x12 for cut stringers
- **Treads**: Horizontal walking surface
  - **Thickness**: Minimum 1" (typically 1.5" or 2x12)
  - **Material**: Hardwood, pine, or composite
- **Risers**: Vertical face between treads
  - **Thickness**: 1/2" to 3/4" typical
  - **Optional** in some cases (open riser stairs)

### Finish
- **Nosing**: Rounded front edge of tread (projects 0.75" to 1.25")
- **Skirt board**: Trim along wall side
- **Handrail**: Graspable rail (34-38" height)
- **Balusters**: Vertical supports (max 4" spacing)
- **Newel post**: Structural posts at ends and landings

## Stringer Layout

### Cut (Open) Stringer
- Uses 2x12 lumber
- Treads sit ON stringer
- Triangular cutouts for each step
- Most common for residential

**Layout Steps**:
1. Mark rise and run on framing square
2. Step off each tread/riser combination
3. Adjust top and bottom for actual connection
4. Cut with circular saw and jigsaw
5. Use first stringer as template

**Critical**: After cutting all risers, drop entire stringer by thickness of tread material (usually 1.5") so first riser equals others.

### Housed Stringer
- Solid 2x12 or wider
- Treads/risers fit INTO routed grooves
- More finished appearance
- More complex to build

## SketchUp Modeling Guidelines

### Setup
1. **Work in inches**
2. **Start with floor-to-floor height**
3. **Calculate riser/tread before modeling**
4. **Use guidelines** for consistency

### Basic Straight Stair Method
1. **Calculate dimensions** using formulas above
2. **Draw first riser** as vertical rectangle (riser height)
3. **Draw first tread** as horizontal rectangle (tread depth)
4. **Create tread+riser group/component**
5. **Copy vertically and horizontally**:
   - Move up by riser height
   - Move forward by tread depth
   - Repeat for number of risers
6. **Draw stringers** using guidelines
7. **Add handrails and balusters**

### Stringer Modeling
1. **Draw 2x12** (1.5" × 11.25") full length
2. **Create rise/run triangle** using guidelines
3. **Copy triangle** along stringer
4. **Use Push/Pull** to remove material (cut stringer)
5. **Or keep solid** (housed stringer appearance)

### Component Strategy
- **Make stringer a component**: Copy for other stringers
- **Make tread/riser assembly component**: Easier to modify all
- **Make baluster component**: Array along length
- **Group complete stair**: Move as single unit

### Best Practices
- **Model to scale**: Always use actual dimensions
- **Check headroom**: Draw ceiling and verify 80" clearance
- **Verify width**: Ensure 36" minimum clear width
- **Landing size**: Must be ≥ stair width
- **Test with guide**: Draw 80" vertical guide for headroom check

## Common Residential Stair Dimensions

### Standard Floor Heights
| Floor-to-Floor | Risers | Riser Height | Treads | Tread Depth | Total Run |
|----------------|--------|--------------|--------|-------------|-----------|
| 8' (96")       | 13     | 7.38"        | 12     | 10.25"      | 123"      |
| 9' (108")      | 14     | 7.71"        | 13     | 10"         | 130"      |
| 10' (120")     | 16     | 7.5"         | 15     | 10"         | 150"      |
| 8'6" (102")    | 14     | 7.29"        | 13     | 10.5"       | 136.5"    |

### Typical Dimensions
- **Width**: 36" (minimum), 42" (comfortable), 48" (generous)
- **Tread depth**: 10-11 inches
- **Riser height**: 7-7.5 inches
- **Nosing projection**: 1 inch
- **Stringer spacing**: 16 inches OC (3 stringers for 36" stair)

## Design Tips

### Comfort Factors
- **Gentler stairs**: Use 7" risers with 11" treads
- **Steeper stairs** (basements): Use 7.75" risers with 10" treads
- **Wider stairs**: Feel more spacious and safer (42-48")
- **Open risers**: Make space feel larger but less comfortable for some

### Safety
- **Consistent dimensions**: Critical for safety
- **Good lighting**: Light at top and bottom
- **Contrasting nosing**: Helps visibility
- **Handrails both sides**: Especially for elderly
- **Non-slip treads**: Important for exterior or basement stairs

### Space Planning
- **Minimum well opening**: Total run + 36" landing
- **Headroom starts**: From nosing of tread where ceiling <80"
- **Door swing**: Must not reduce landing to less than stair width
- **Landing at doors**: Top of stairs should have full landing (not a tread)

## Common Mistakes in SketchUp

1. **Wrong riser count**: Remember treads = risers - 1
2. **Inconsistent dimensions**: Every riser and tread must match
3. **Forgetting nosing**: Affects tread depth calculation
4. **Ignoring headroom**: Check clearance along entire run
5. **Incorrect stringer drop**: First riser will be wrong if not adjusted
6. **Wrong stringer depth**: Need 11.25" (2x12) minimum for cut stringers
7. **Balusters too far apart**: Max 4" spacing per code
8. **Landing too small**: Must be at least stair width

## Quick Checks

Before finalizing stairs, verify:
- [ ] Riser height ≤ 7.75"
- [ ] Tread depth ≥ 10"
- [ ] 2R + T = 24-25"
- [ ] Headroom ≥ 80" throughout
- [ ] Width ≥ 36" clear
- [ ] All risers equal (within 3/8")
- [ ] All treads equal
- [ ] Handrails at 34-38" height
- [ ] Landing ≥ 36" × 36" (or stair width)
