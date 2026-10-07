"""
tests/test_collector.py - Unit tests for PlacesCollector geocoding and mock datasets.
"""

import unittest
from collectors.places import PlacesCollector


class TestPlacesCollector(unittest.TestCase):
    def setUp(self):
        self.collector = PlacesCollector(use_mock=True)

    def test_geocode_known_pincodes(self):
        lat, lng, label = self.collector.geocode_target(pincode="500034")
        self.assertAlmostEqual(lat, 17.4156, places=2)
        self.assertAlmostEqual(lng, 78.4357, places=2)
        self.assertIn("Banjara Hills", label)

    def test_geocode_known_areas(self):
        lat, lng, label = self.collector.geocode_target(area="Madhapur")
        self.assertAlmostEqual(lat, 17.4483, places=2)
        self.assertAlmostEqual(lng, 78.3915, places=2)
        self.assertIn("Madhapur", label)

    def test_mock_generation_tier1(self):
        data = self.collector.collect_all_categories(
            lat=17.4156,
            lng=78.4357,
            pincode="500034",
            area="Banjara Hills"
        )
        self.assertTrue(data["is_mock"])
        venues = data["venues"]
        self.assertGreater(len(venues), 10)
        luxury_venues = [v for v in venues if "luxury_automotive" in v.get("categories", [])]
        self.assertGreaterEqual(len(luxury_venues), 3)

    def test_mock_generation_tier2(self):
        data = self.collector.collect_all_categories(
            lat=17.4483,
            lng=78.3915,
            pincode="500081",
            area="Madhapur"
        )
        venues = data["venues"]
        dining_venues = [v for v in venues if "premium_dining" in v.get("categories", [])]
        self.assertGreaterEqual(len(dining_venues), 5)


    def test_cache_save_and_load(self):
        import shutil
        import tempfile
        tmp_dir = tempfile.mkdtemp()
        try:
            collector = PlacesCollector(use_mock=False, cache_dir=tmp_dir)
            sample_data = {
                "venues": [{"id": "v1", "name": "Test Venue", "categories": ["luxury_automotive"]}],
                "bucket_results": {"luxury_automotive": {"count": 1, "venues": ["Test Venue"]}},
                "is_mock": False
            }
            collector._save_to_cache(pincode="500034", area="Banjara Hills", radius=4000, data=sample_data)
            
            cached = collector._load_from_cache(pincode="500034", area="Banjara Hills", radius=4000)
            self.assertIsNotNone(cached)
            self.assertEqual(len(cached["venues"]), 1)
            self.assertEqual(cached["venues"][0]["name"], "Test Venue")
            self.assertTrue(cached.get("from_cache"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

