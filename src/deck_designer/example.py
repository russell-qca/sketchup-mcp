"""
Example usage of the deck calculator
"""

from deck_designer.code_loader import BuildingCode
from deck_designer.calculations import DeckCalculator, DeckDimensions
import json


def main():
    """Example: Calculate a 12' × 16' ground-level deck"""

    print("=" * 70)
    print("DECK STRUCTURAL CALCULATIONS")
    print("=" * 70)

    # Load building code
    code = BuildingCode.load("ohio_2019")
    print(f"\nBuilding Code: {code.code_name}")
    print(f"Jurisdiction: {code.jurisdiction}")

    # Create calculator
    calc = DeckCalculator(code)

    # Define deck dimensions
    deck = DeckDimensions(
        length=12 * 12,  # 12 feet = 144 inches (parallel to house)
        width=16 * 12,   # 16 feet = 192 inches (perpendicular to house)
        height=24        # 24 inches above grade
    )

    print(f"\nDeck Dimensions:")
    print(f"  Length: {deck.length / 12:.1f}' (parallel to house)")
    print(f"  Width: {deck.width / 12:.1f}' (joists span)")
    print(f"  Height: {deck.height}\" above grade")
    print(f"  Area: {(deck.length * deck.width) / 144:.1f} sqft")

    # Calculate structural design
    results = calc.calculate_deck(
        dimensions=deck,
        joist_spacing=16,  # 16" on-center
        species="Southern_Pine"
    )

    # Display results
    print("\n" + "-" * 70)
    print("JOIST SIZING")
    print("-" * 70)
    j = results['joists']
    print(f"  Size: {j['size']} {j['species']}")
    print(f"  Spacing: {j['spacing_inches']}\" on-center")
    print(f"  Required span: {j['required_span_ft']:.1f}'")
    print(f"  Maximum span: {j['max_span_ft']:.1f}'")
    print(f"  Status: {'✓ COMPLIANT' if j['compliant'] else '✗ NON-COMPLIANT'}")
    print(f"  {j['notes']}")

    print("\n" + "-" * 70)
    print("BEAM SIZING")
    print("-" * 70)
    b = results['beams']
    print(f"  Size: {b['size']} {b['species']}")
    print(f"  Tributary width: {b['tributary_width_ft']}'")
    print(f"  Required span: {b['required_span_ft']:.1f}'")
    print(f"  Maximum span: {b['max_span_ft']:.1f}'")
    print(f"  Status: {'✓ COMPLIANT' if b['compliant'] else '✗ NON-COMPLIANT'}")
    print(f"  {b['notes']}")

    print("\n" + "-" * 70)
    print("TRIBUTARY LOAD ANALYSIS")
    print("-" * 70)
    for trib in results['tributary_loads']:
        print(f"  {trib['description']}")
        print(f"    Dead load: {trib['dead_load_psf']} psf")
        print(f"    Live load: {trib['live_load_psf']} psf")
        print(f"    Total load: {trib['total_load_lbs']:.0f} lbs")

    print("\n" + "-" * 70)
    print("POST SIZING")
    print("-" * 70)
    p = results['posts']
    print(f"  Size: {p['size']}")
    print(f"  Height: {p['height_ft']:.1f}'")
    print(f"  Load: {p['load_lbs']:.0f} lbs")
    print(f"  Capacity: {p['capacity_lbs']} lbs")
    print(f"  Safety factor: {p['safety_factor']:.2f}")
    print(f"  Status: {'✓ COMPLIANT' if p['compliant'] else '✗ NON-COMPLIANT'}")
    print(f"  {p['notes']}")

    print("\n" + "-" * 70)
    print("FOOTING SIZING")
    print("-" * 70)
    f = results['footings']
    print(f"  Diameter: {f['diameter_inches']}\"")
    print(f"  Depth: {f['depth_inches']}\" (below grade)")
    print(f"  Load: {f['load_lbs']:.0f} lbs")
    print(f"  Bearing pressure: {f['bearing_pressure_psf']:.0f} psf")
    print(f"  Soil capacity: {f['soil_bearing_capacity_psf']} psf")
    print(f"  Safety factor: {f['safety_factor']:.2f}")
    print(f"  Status: {'✓ COMPLIANT' if f['compliant'] else '✗ NON-COMPLIANT'}")
    print(f"  {f['notes']}")

    print("\n" + "=" * 70)
    print(f"OVERALL COMPLIANCE: {'✓ PASS' if results['compliant'] else '✗ FAIL'}")
    print("=" * 70)

    if results['warnings']:
        print("\nWARNINGS:")
        for warning in results['warnings']:
            print(f"  ⚠ {warning}")

    if results['errors']:
        print("\nERRORS:")
        for error in results['errors']:
            print(f"  ✗ {error}")

    # Save to JSON
    output_file = "deck_calculations.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    main()
