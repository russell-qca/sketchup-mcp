"""
Structural calculations for deck design
Performs tributary load analysis, member sizing, and code compliance checks
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from .code_loader import BuildingCode
import math


@dataclass
class DeckDimensions:
    """Deck dimensions in inches"""
    length: float  # inches (parallel to house)
    width: float   # inches (perpendicular to house)
    height: float  # inches above grade


@dataclass
class StructuralMember:
    """Represents a structural member with sizing and compliance"""
    member_type: str  # "joist", "beam", "post", "footing"
    size: str  # e.g., "2x8", "4x4", "12in diameter"
    span: float  # inches
    spacing: Optional[float]  # inches (for joists/beams)
    load: float  # pounds or psf
    capacity: float  # pounds or inches (max span)
    compliant: bool
    notes: str


@dataclass
class TributaryLoad:
    """Tributary load calculation result"""
    area_sqft: float
    dead_load_psf: float
    live_load_psf: float
    total_load_psf: float
    total_load_lbs: float
    description: str


class DeckCalculator:
    """Performs structural calculations for deck design"""

    def __init__(self, building_code: BuildingCode):
        self.code = building_code
        self.loads = building_code.get_loads()

    def calculate_deck(self,
                      dimensions: DeckDimensions,
                      joist_spacing: int = 16,
                      species: str = "Southern_Pine") -> Dict[str, Any]:
        """
        Complete deck structural calculation

        Args:
            dimensions: DeckDimensions object
            joist_spacing: Joist spacing in inches (12, 16, or 24)
            species: Lumber species

        Returns:
            Dict with all calculations and compliance checks
        """
        results = {
            'dimensions': {
                'length_ft': dimensions.length / 12,
                'width_ft': dimensions.width / 12,
                'height_in': dimensions.height,
                'area_sqft': (dimensions.length * dimensions.width) / 144
            },
            'code': {
                'name': self.code.code_name,
                'jurisdiction': self.code.jurisdiction
            },
            'loads': self.loads,
            'joists': None,
            'beams': None,
            'posts': None,
            'footings': None,
            'tributary_loads': [],
            'compliant': True,
            'warnings': [],
            'errors': []
        }

        # 1. Size joists
        joist_result = self.size_joists(
            span_inches=dimensions.width,
            spacing_inches=joist_spacing,
            species=species
        )
        results['joists'] = joist_result

        if not joist_result['compliant']:
            results['compliant'] = False
            results['errors'].append(f"Joists: {joist_result['notes']}")

        # 2. Size beams (assuming beam at each end for ground-level deck)
        beam_result = self.size_beams(
            joist_span_inches=dimensions.width,
            beam_span_inches=dimensions.length,
            joist_spacing_inches=joist_spacing,
            species=species
        )
        results['beams'] = beam_result

        if not beam_result['compliant']:
            results['compliant'] = False
            results['errors'].append(f"Beams: {beam_result['notes']}")

        # 3. Calculate tributary loads and size posts
        tributary_load = self.calculate_tributary_load_for_post(
            beam_span_ft=dimensions.length / 12,
            joist_span_ft=dimensions.width / 12,
            description="Corner post"
        )
        results['tributary_loads'].append(tributary_load.__dict__)

        post_result = self.size_posts(
            load_lbs=tributary_load.total_load_lbs,
            height_inches=dimensions.height
        )
        results['posts'] = post_result

        if not post_result['compliant']:
            results['compliant'] = False
            results['errors'].append(f"Posts: {post_result['notes']}")

        # 4. Size footings
        footing_result = self.size_footings(
            load_lbs=tributary_load.total_load_lbs
        )
        results['footings'] = footing_result

        if not footing_result['compliant']:
            results['compliant'] = False
            results['errors'].append(f"Footings: {footing_result['notes']}")

        # 5. Check height for railing requirement
        if dimensions.height > 30:
            results['warnings'].append(
                f"Deck height ({dimensions.height:.1f}\") exceeds 30\" - guardrails required"
            )

        return results

    def size_joists(self,
                   span_inches: float,
                   spacing_inches: int = 16,
                   species: str = "Southern_Pine") -> Dict[str, Any]:
        """
        Determine appropriate joist size

        Returns:
            Dict with joist size, max span, compliance
        """
        # Try sizes from smallest to largest
        sizes = ["2x6", "2x8", "2x10", "2x12"]

        for size in sizes:
            max_span = self.code.get_joist_span(size, species, spacing_inches)

            if max_span and max_span >= span_inches:
                return {
                    'member_type': 'joist',
                    'size': size,
                    'species': species,
                    'spacing_inches': spacing_inches,
                    'required_span_inches': span_inches,
                    'required_span_ft': span_inches / 12,
                    'max_span_inches': max_span,
                    'max_span_ft': max_span / 12,
                    'compliant': True,
                    'notes': f"{size} {species} @ {spacing_inches}\" OC spans {max_span / 12:.1f}' (required: {span_inches / 12:.1f}')"
                }

        # No size works
        return {
            'member_type': 'joist',
            'size': 'NONE',
            'species': species,
            'spacing_inches': spacing_inches,
            'required_span_inches': span_inches,
            'required_span_ft': span_inches / 12,
            'max_span_inches': 0,
            'max_span_ft': 0,
            'compliant': False,
            'notes': f"No joist size can span {span_inches / 12:.1f}' at {spacing_inches}\" OC. Reduce span or add a mid-beam."
        }

    def size_beams(self,
                  joist_span_inches: float,
                  beam_span_inches: float,
                  joist_spacing_inches: int = 16,
                  species: str = "Southern_Pine") -> Dict[str, Any]:
        """
        Determine appropriate beam size (double 2x)

        Args:
            joist_span_inches: How far joists span (tributary width for beam)
            beam_span_inches: How far beam must span
            joist_spacing_inches: Joist spacing
            species: Lumber species

        Returns:
            Dict with beam size, max span, compliance
        """
        # Beam span tables are based on joist span in feet
        joist_span_ft = round(joist_span_inches / 12)

        # Ensure we have a valid table entry (6, 8, 10, or 12 ft)
        table_spans = [6, 8, 10, 12]
        joist_span_table = min(table_spans, key=lambda x: abs(x - joist_span_ft))

        # Try sizes from smallest to largest
        sizes = ["2x6", "2x8", "2x10", "2x12"]

        for size in sizes:
            max_span = self.code.get_beam_span(size, species, joist_span_table)

            if max_span and max_span >= beam_span_inches:
                return {
                    'member_type': 'beam',
                    'size': f"(2) {size}",
                    'species': species,
                    'tributary_width_ft': joist_span_ft,
                    'required_span_inches': beam_span_inches,
                    'required_span_ft': beam_span_inches / 12,
                    'max_span_inches': max_span,
                    'max_span_ft': max_span / 12,
                    'compliant': True,
                    'notes': f"Double {size} {species} beam spans {max_span / 12:.1f}' with {joist_span_table}' tributary (required: {beam_span_inches / 12:.1f}')"
                }

        # No size works
        return {
            'member_type': 'beam',
            'size': 'NONE',
            'species': species,
            'tributary_width_ft': joist_span_ft,
            'required_span_inches': beam_span_inches,
            'required_span_ft': beam_span_inches / 12,
            'max_span_inches': 0,
            'max_span_ft': 0,
            'compliant': False,
            'notes': f"No beam size can span {beam_span_inches / 12:.1f}' with {joist_span_table}' tributary. Add intermediate posts."
        }

    def calculate_tributary_load_for_post(self,
                                         beam_span_ft: float,
                                         joist_span_ft: float,
                                         description: str = "Post") -> TributaryLoad:
        """
        Calculate tributary load for a single post

        Tributary area is (beam_span / 2) × (joist_span / 2) for corner posts
        For intermediate posts, full beam span

        Args:
            beam_span_ft: Beam span in feet
            joist_span_ft: Joist span in feet
            description: Description of load area

        Returns:
            TributaryLoad object
        """
        # For corner post, take half of each span
        # For intermediate post, would take full beam span
        area_sqft = (beam_span_ft / 2) * (joist_span_ft / 2)

        dead_load_psf = self.loads.get('dead_load_psf', 10)
        live_load_psf = self.loads.get('live_load_psf', 40)
        total_load_psf = dead_load_psf + live_load_psf

        total_load_lbs = area_sqft * total_load_psf

        return TributaryLoad(
            area_sqft=area_sqft,
            dead_load_psf=dead_load_psf,
            live_load_psf=live_load_psf,
            total_load_psf=total_load_psf,
            total_load_lbs=total_load_lbs,
            description=f"{description}: {area_sqft:.1f} sqft @ {total_load_psf} psf"
        )

    def size_posts(self,
                  load_lbs: float,
                  height_inches: float = 24) -> Dict[str, Any]:
        """
        Determine appropriate post size

        Args:
            load_lbs: Total load on post in pounds
            height_inches: Post height in inches

        Returns:
            Dict with post size and compliance
        """
        # For ground-level decks (<30"), 4x4 is typically sufficient
        # Check against code capacities
        sizes = ["4x4", "4x6", "6x6"]

        for size in sizes:
            capacity = self.code.get_post_capacity(size)

            if capacity and capacity >= load_lbs:
                return {
                    'member_type': 'post',
                    'size': size,
                    'height_inches': height_inches,
                    'height_ft': height_inches / 12,
                    'load_lbs': load_lbs,
                    'capacity_lbs': capacity,
                    'safety_factor': capacity / load_lbs,
                    'compliant': True,
                    'notes': f"{size} post supports {load_lbs:.0f} lbs (capacity: {capacity} lbs, SF: {capacity/load_lbs:.2f})"
                }

        # No size works (rare for ground-level decks)
        return {
            'member_type': 'post',
            'size': 'NONE',
            'height_inches': height_inches,
            'load_lbs': load_lbs,
            'capacity_lbs': 0,
            'compliant': False,
            'notes': f"Load of {load_lbs:.0f} lbs exceeds standard post capacity. Consult engineer."
        }

    def size_footings(self, load_lbs: float) -> Dict[str, Any]:
        """
        Determine footing size

        Args:
            load_lbs: Total load on footing in pounds

        Returns:
            Dict with footing size and compliance
        """
        footing_reqs = self.code.get_footing_requirements()
        soil_bearing = footing_reqs.get('soil_bearing_capacity_psf', 1500)
        min_diameter = footing_reqs.get('min_diameter_inches', 12)
        min_depth = footing_reqs.get('min_depth_inches', 32)

        # Required footing area based on soil bearing capacity
        required_area_sqft = load_lbs / soil_bearing

        # Calculate diameter for circular footing
        required_diameter_inches = math.sqrt(required_area_sqft * 144 / math.pi) * 2

        # Use larger of required or minimum code diameter
        diameter_inches = max(required_diameter_inches, min_diameter)

        # Round up to nearest 2 inches
        diameter_inches = math.ceil(diameter_inches / 2) * 2

        actual_area_sqft = math.pi * (diameter_inches / 2) ** 2 / 144
        bearing_pressure_psf = load_lbs / actual_area_sqft

        return {
            'member_type': 'footing',
            'diameter_inches': diameter_inches,
            'depth_inches': min_depth,
            'load_lbs': load_lbs,
            'area_sqft': actual_area_sqft,
            'soil_bearing_capacity_psf': soil_bearing,
            'bearing_pressure_psf': bearing_pressure_psf,
            'safety_factor': soil_bearing / bearing_pressure_psf,
            'compliant': bearing_pressure_psf <= soil_bearing,
            'notes': f"{diameter_inches}\" diameter × {min_depth}\" deep footing, bearing pressure: {bearing_pressure_psf:.0f} psf (capacity: {soil_bearing} psf)"
        }
