"""
Building code loader - Loads and parses building code data from JSON files
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import re


class BuildingCode:
    """Represents a building code with span tables and requirements"""

    def __init__(self, code_data: Dict[str, Any]):
        self.data = code_data
        self.code_name = code_data.get('code_name', 'Unknown')
        self.jurisdiction = code_data.get('jurisdiction', 'Unknown')

    @classmethod
    def load(cls, code_name: str = "ohio_2019") -> 'BuildingCode':
        """Load a building code from the codes directory"""
        codes_dir = Path(__file__).parent / "codes"
        code_file = codes_dir / f"{code_name}.json"

        if not code_file.exists():
            raise FileNotFoundError(f"Building code file not found: {code_file}")

        with open(code_file, 'r') as f:
            code_data = json.load(f)

        return cls(code_data)

    def get_loads(self) -> Dict[str, float]:
        """Get load requirements (psf)"""
        return self.data.get('loads', {})

    def get_joist_span(self,
                      lumber_size: str,
                      species: str,
                      spacing_inches: int) -> Optional[float]:
        """
        Get maximum joist span in inches

        Args:
            lumber_size: e.g., "2x6", "2x8", "2x10"
            species: e.g., "Southern_Pine", "Douglas_Fir_Larch", "SPF"
            spacing_inches: Joist spacing in inches (12, 16, or 24)

        Returns:
            Maximum span in inches, or None if not found
        """
        try:
            span_str = (self.data['joist_spans']['species']
                       [species][lumber_size][str(spacing_inches)])
            return self._parse_feet_inches(span_str)
        except KeyError:
            return None

    def get_beam_span(self,
                     lumber_size: str,
                     species: str,
                     joist_span_feet: int) -> Optional[float]:
        """
        Get maximum beam span in inches for double 2x beam

        Args:
            lumber_size: e.g., "2x6", "2x8", "2x10", "2x12"
            species: e.g., "Southern_Pine", "Douglas_Fir_Larch", "SPF"
            joist_span_feet: Distance joists span to next beam (feet)

        Returns:
            Maximum beam span in inches, or None if not found
        """
        try:
            span_str = (self.data['beam_spans']['species']
                       [species][lumber_size][str(joist_span_feet)])
            return self._parse_feet_inches(span_str)
        except KeyError:
            return None

    def get_footing_requirements(self) -> Dict[str, Any]:
        """Get footing requirements"""
        return self.data.get('footings', {})

    def get_frost_depth(self) -> int:
        """Get frost depth in inches"""
        return self.data.get('frost_depth', {}).get('depth_inches', 32)

    def get_post_capacity(self, post_size: str) -> Optional[int]:
        """Get post load capacity in pounds"""
        posts = self.data.get('posts', {}).get('sizes', {})
        post_data = posts.get(post_size, {})
        return post_data.get('max_load_lbs')

    @staticmethod
    def _parse_feet_inches(span_str: str) -> float:
        """
        Parse feet-inches format to total inches

        Examples:
            "10-6" -> 126.0 (10 feet 6 inches)
            "8-0" -> 96.0 (8 feet)
            "11-7" -> 139.0 (11 feet 7 inches)

        Args:
            span_str: Span in "feet-inches" format

        Returns:
            Total span in inches
        """
        match = re.match(r'(\d+)-(\d+)', span_str)
        if not match:
            raise ValueError(f"Invalid span format: {span_str}")

        feet = int(match.group(1))
        inches = int(match.group(2))
        return feet * 12 + inches

    @staticmethod
    def inches_to_feet_inches(inches: float) -> str:
        """
        Convert inches to feet-inches format

        Args:
            inches: Total inches

        Returns:
            String in "feet-inches" format
        """
        feet = int(inches // 12)
        remaining_inches = int(inches % 12)
        return f"{feet}'-{remaining_inches}\""
