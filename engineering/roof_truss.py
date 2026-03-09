# Wood Roof Truss Geometry Calculator
# =====================================
# Inputs:  span (ft), pitch (rise/run as integer, e.g. 6 for 6/12)
# Outputs: complete geometry for a standard Fink (W) truss
#
#           Ridge
#             /\
#            /  \
#           /    \
#          /  /\  \
#         /  /  \  \
#        /__/____\__\
#       L              R
#       |<--- span --->|
#
# Members:  TC = Top Chord (rafter)
#           BC = Bottom Chord (ceiling joist)
#           W  = Web members (verticals & diagonals)

import math


def calculate_truss_geometry(span_ft: float, pitch: int) -> dict:
    """
    Calculate complete Fink truss geometry.

    Parameters
    ----------
    span_ft : float
        Total horizontal span of the truss in feet (wall plate to wall plate).
    pitch : int
        Roof pitch expressed as rise per 12 inches of run (e.g. 6 for 6/12).

    Returns
    -------
    dict with all geometry values (feet and degrees).
    """

    # ── 1. Basic triangle ────────────────────────────────────────────────────
    half_span = span_ft / 2                          # horizontal run each side
    rise      = (pitch / 12) * half_span             # vertical rise to ridge
    rafter_len = math.sqrt(half_span**2 + rise**2)  # top chord length each side

    pitch_angle_deg = math.degrees(math.atan(rise / half_span))

    # ── 2. Span / truss depth ratio (efficiency check: target 10–15) ───────────
    # Truss depth = rise (bottom chord to ridge). 10-15 is the optimal slenderness range.
    truss_depth = rise
    span_height_ratio = span_ft / truss_depth if truss_depth > 0 else float('inf')

    # ── 3. Fink (W) truss web layout ─────────────────────────────────────────
    #
    #  Panel points divide the bottom chord into thirds (standard Fink).
    #  Quarter-span verticals rise to meet diagonal webs from the ridge.
    #
    #  Node labelling (left → right):
    #   A = bottom-left (bearing)
    #   B = 1/4-span along bottom chord
    #   C = 1/2-span (centre, below ridge)
    #   D = 3/4-span along bottom chord
    #   E = bottom-right (bearing)
    #   F = ridge (top centre)
    #   G = top chord @ 1/4 span  (left)
    #   H = top chord @ 3/4 span  (right)

    nodes = {
        "A": (0.0,           0.0),
        "B": (span_ft / 4,   0.0),
        "C": (span_ft / 2,   0.0),
        "D": (3 * span_ft / 4, 0.0),
        "E": (span_ft,       0.0),
        "F": (span_ft / 2,   rise),          # ridge
        "G": (span_ft / 4,   rise / 2),      # midpoint of left top chord
        "H": (3 * span_ft / 4, rise / 2),    # midpoint of right top chord
    }

    # ── 4. Members ────────────────────────────────────────────────────────────
    members = {
        # Top chord (2 segments each side)
        "TC-Left-1":  ("A", "G"),
        "TC-Left-2":  ("G", "F"),
        "TC-Right-1": ("F", "H"),
        "TC-Right-2": ("H", "E"),

        # Bottom chord (4 segments)
        "BC-1": ("A", "B"),
        "BC-2": ("B", "C"),
        "BC-3": ("C", "D"),
        "BC-4": ("D", "E"),

        # Verticals
        "V-Left":  ("B", "G"),
        "V-Center": ("C", "F"),
        "V-Right": ("D", "H"),

        # Diagonals
        "D-Left":  ("A", "G"),   # same as TC-Left-1 in a true Fink;
                                  # shown separately for clarity
        "D-CL":    ("B", "F"),   # diagonal from B up to ridge
        "D-CR":    ("D", "F"),   # diagonal from D up to ridge
        "D-Right": ("E", "H"),   # same as TC-Right-2 mirrored
    }

    # Compute each member length
    def dist(n1, n2):
        x1, y1 = nodes[n1]
        x2, y2 = nodes[n2]
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    # Core member lengths (named clearly)
    member_lengths = {}
    for name, (n1, n2) in members.items():
        member_lengths[name] = round(dist(n1, n2), 4)

    # ── 5. Angles ─────────────────────────────────────────────────────────────
    # Diagonal web angle relative to bottom chord (horizontal)
    web_diag_rise = rise / 2        # G and H are at rise/2
    web_diag_run  = span_ft / 4
    web_diag_angle = math.degrees(math.atan(web_diag_rise / web_diag_run))

    # ── 6. Truss count for a given building length ────────────────────────────
    # Provided as a helper formula — user can call separately.

    return {
        "inputs": {
            "span_ft":  span_ft,
            "pitch":    f"{pitch}/12",
        },
        "primary_geometry": {
            "half_span_ft":         round(half_span, 4),
            "rise_ft":              round(rise, 4),
            "rafter_length_ft":     round(rafter_len, 4),
            "pitch_angle_deg":      round(pitch_angle_deg, 2),
            "span_height_ratio":    round(span_height_ratio, 2),
        },
        "nodes_xy_ft":  {k: (round(v[0], 4), round(v[1], 4)) for k, v in nodes.items()},
        "member_lengths_ft": member_lengths,
        "web_diagonal_angle_deg": round(web_diag_angle, 2),
        "efficiency_check": {
            "span_height_ratio":  round(span_height_ratio, 2),
            "pitch_angle_deg":    round(pitch_angle_deg, 2),
            # Residential pitches: 4/12–9/12 are ideal (18°–37°)
            # <4/12 = drainage/snow issues; >9/12 = high wind exposure
            "pitch_category": (
                "⚠️  Too shallow — drainage/snow load risk (min 4/12 recommended)"
                if pitch < 4 else
                "✅ Typical residential pitch"
                if 4 <= pitch <= 9 else
                "⚠️  Steep pitch — increased wind exposure and material costs"
            ),
        },
    }


def truss_count(roof_length_ft: float) -> int:
    """Number of trusses needed for a given roof length (24-inch OC spacing)."""
    return int((roof_length_ft * 12) / 24) + 1


def print_report(span_ft: float, pitch: int) -> None:
    """Pretty-print the full geometry report."""
    g = calculate_truss_geometry(span_ft, pitch)

    print("=" * 56)
    print("  WOOD ROOF TRUSS GEOMETRY REPORT")
    print("=" * 56)

    print(f"\n  Span : {g['inputs']['span_ft']} ft")
    print(f"  Pitch: {g['inputs']['pitch']}")

    print("\n── PRIMARY GEOMETRY ─────────────────────────────────")
    pg = g["primary_geometry"]
    print(f"  Half span (run)   : {pg['half_span_ft']} ft")
    print(f"  Rise              : {pg['rise_ft']} ft")
    print(f"  Rafter length     : {pg['rafter_length_ft']} ft  (each side)")
    print(f"  Pitch angle       : {pg['pitch_angle_deg']}°")
    print(f"  Span/height ratio : {pg['span_height_ratio']}")

    print("\n── NODE COORDINATES (ft)  ───────────────────────────")
    print("  Node   X         Y")
    for node, (x, y) in g["nodes_xy_ft"].items():
        print(f"   {node}    {x:<8}  {y}")

    print("\n── MEMBER LENGTHS (ft)  ─────────────────────────────")
    seen = set()
    for name, length in g["member_lengths_ft"].items():
        if length not in seen or name.startswith("D-"):
            print(f"  {name:<14}: {length} ft")
        seen.add(length)

    print(f"\n  Web diagonal angle : {g['web_diagonal_angle_deg']}° from horizontal")

    print("\n── EFFICIENCY CHECK ─────────────────────────────────")
    ec = g["efficiency_check"]
    print(f"  Span/height ratio : {ec['span_height_ratio']}")
    print(f"  Pitch angle       : {ec['pitch_angle_deg']}°")
    print(f"  Pitch category    : {ec['pitch_category']}")

    print("\n── TRUSS COUNT HELPER ───────────────────────────────")
    print("  Formula: count = (roof_length_ft × 12 / 24) + 1")
    print("  Examples:")
    for l in [24, 30, 40, 50]:
        print(f"    {l} ft building → {truss_count(l)} trusses  (@ 24\" OC)")

    print("=" * 56)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3:
        span  = float(sys.argv[1])
        pitch = int(sys.argv[2])
    else:
        # Default example
        print("Usage: python truss_geometry.py <span_ft> <pitch>")
        print("Example: python truss_geometry.py 32 6\n")
        span, pitch = 32, 6

    print_report(span, pitch)