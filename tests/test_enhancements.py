import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to sys.path so we can import backend packages
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.schemas import BrandRequest
from app.api.generator_router import generate_names
from app.api.logo_router import parse_color_to_rgb, draw_procedural_logo

class TestBrandCraftEnhancements(unittest.TestCase):

    @patch('app.api.generator_router.genai.GenerativeModel')
    @patch('app.api.generator_router.HAS_GEMINI_KEY', True)
    def test_generate_names_gemini_uniqueness(self, mock_model_class):
        """Test that generate_names handles Gemini API response and enforces uniqueness."""
        # Mock genai response with duplicate names
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "brands": [
                {"name": "NovaSpark", "meaning": "Creative", "tagline": "Spark new ideas", "domains": ["novaspark.com"]},
                {"name": "NovaSpark", "meaning": "Creative", "tagline": "Spark new ideas", "domains": ["novaspark.com"]},
                {"name": "VertexFlow", "meaning": "Apex flow", "tagline": "Flow to top", "domains": ["vertexflow.com"]}
            ]
        }'''
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        req = BrandRequest(
            business_type="SaaS",
            industry="Technology",
            target_audience="Developers",
            brand_personality="Bold",
            preferred_language="English",
            country="USA"
        )
        
        result = generate_names(req, current_user=MagicMock())
        brands = result.get("brands", [])
        
        # Verify duplicates are stripped and only 2 unique brands remain
        self.assertEqual(len(brands), 2)
        names = [b["name"] for b in brands]
        self.assertEqual(names, ["NovaSpark", "VertexFlow"])

    def test_color_parsing(self):
        """Test parse_color_to_rgb parses hex values and named colors correctly."""
        # Hex with hash
        self.assertEqual(parse_color_to_rgb("#C9758A"), (201, 117, 138))
        # Hex without hash
        self.assertEqual(parse_color_to_rgb("c9758a"), (201, 117, 138))
        # Short hex
        self.assertEqual(parse_color_to_rgb("#fff"), (255, 255, 255))
        # Named color
        self.assertEqual(parse_color_to_rgb("teal"), (0, 128, 128))
        # Fallback for invalid color
        self.assertEqual(parse_color_to_rgb("not-a-color"), (216, 27, 96))

    def test_draw_procedural_logo_custom_color(self):
        """Test that draw_procedural_logo executes without error with custom hex color."""
        # Draw with a custom hex color
        img = draw_procedural_logo(
            brand_name="NovaSpark",
            industry="Tech",
            style="Minimal",
            color_theme="#C9758A",
            logo_type="emblem",
            seed=0
        )
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (800, 800))

if __name__ == "__main__":
    unittest.main()
