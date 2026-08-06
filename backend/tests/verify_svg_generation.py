
import asyncio
import os
import sys
import unittest

# Add the project root to the Python path to resolve import issues
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.app.services.assets.images import AssetService
from backend.app.services.assets.shared.asset_item import AssetItem

class TestSVGGeneration(unittest.TestCase):

    def test_svg_writer_agent_produces_valid_svg(self):
        """
        Tests that the AssetService, using the new SVG Writer Agent,
        can generate a valid SVG asset from a simple visual cue.
        """
        async def run_test():
            # 1. Initialize the AssetService
            asset_service = AssetService()

            # 2. Define a test case
            cue = "a friendly robot waving hello"
            scene_id = "scene_01"
            cue_id = "cue_01"
            asset_id = "asset_01"
            video_id = "video_01"

            # 3. Call the resolver to generate the SVG asset
            generated_asset = await asset_service.resolve_visual_cue(
                cue=cue,
                scene_id=scene_id,
                cue_id=cue_id,
                asset_id=asset_id,
                video_id=video_id,
                supabase_client=None
            )

            # 4. Assert the results
            self.assertIsInstance(generated_asset, AssetItem, "The service should return an AssetItem")
            self.assertEqual(generated_asset.asset_type, "svg", "The asset type should be 'svg'")
            self.assertEqual(generated_asset.resolution, "vector", "The resolution should be 'vector'")
            
            svg_code = generated_asset.prompt
            self.assertIsNotNone(svg_code, "The SVG code should not be null")
            self.assertTrue(svg_code.strip().startswith("<svg"), "The output should start with an <svg> tag")
            self.assertTrue(svg_code.strip().endswith("</svg>"), "The output should end with an </svg> tag")
            self.assertNotIn("LLM not available", svg_code, "The LLM should be available and used")
            self.assertNotIn("SVG generation failed", svg_code, "The SVG generation should not fail")

        # Run the async test
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()