"""
tests/test_analyzer.py - Unit tests for AffluenceAnalyzer and RealEstateProxyStore.
"""

import unittest
from analyzer import AffluenceAnalyzer, RealEstateProxyStore


class TestRealEstateProxyStore(unittest.TestCase):
    def setUp(self):
        self.store = RealEstateProxyStore()

    def test_known_pincode_lookup(self):
        proxy = self.store.get_proxy(pincode="500034")
        self.assertEqual(proxy["benchmark_tier"], "Tier 1")
        self.assertGreaterEqual(proxy["avg_rent_sqft_inr"], 70.0)

    def test_area_name_lookup(self):
        proxy = self.store.get_proxy(area="Madhapur")
        self.assertEqual(proxy["benchmark_tier"], "Tier 2")

    def test_custom_proxy_ingestion(self):
        import tempfile
        import json
        import os

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "500099": {
                    "area_name": "Custom Tech Valley",
                    "avg_rent_sqft_inr": 65.0,
                    "avg_cost_for_two_inr": 2000.0,
                    "benchmark_tier": "Tier 2",
                    "archetype": "Test Archetype"
                }
            }, f)
            temp_path = f.name

        try:
            custom_store = RealEstateProxyStore(custom_proxy_path=temp_path)
            res = custom_store.get_proxy(pincode="500099")
            self.assertEqual(res["area_name"], "Custom Tech Valley")
            self.assertEqual(res["avg_rent_sqft_inr"], 65.0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestAffluenceAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = AffluenceAnalyzer()

    def test_tier1_classification(self):
        # Sample venues representing Banjara Hills
        venues = [
            {"id": "v1", "name": "Porsche Showroom", "categories": ["luxury_automotive"], "rating": 4.8, "userRatingCount": 500},
            {"id": "v2", "name": "BMW Showroom", "categories": ["luxury_automotive"], "rating": 4.7, "userRatingCount": 1000},
            {"id": "v3", "name": "Fine Dining Restobar", "categories": ["premium_dining"], "rating": 4.5, "userRatingCount": 5000},
            {"id": "v4", "name": "Gourmet Pantry", "categories": ["premium_retail"], "rating": 4.6, "userRatingCount": 2000},
        ]
        result = self.analyzer.analyze(venues=venues, pincode="500034", area="Banjara Hills")
        self.assertEqual(result["classification"]["tier"], "Tier 1")
        self.assertGreaterEqual(result["scores"]["affluence_score"], 75.0)
        self.assertEqual(result["scores"]["premium_density_pct"], 100.0)

    def test_tier2_classification(self):
        # Sample venues representing Madhapur / IT Corridor
        venues = [
            {"id": "v1", "name": "Craft Brewery A", "categories": ["premium_dining"], "rating": 4.6, "userRatingCount": 15000},
            {"id": "v2", "name": "Craft Brewery B", "categories": ["premium_dining"], "rating": 4.5, "userRatingCount": 12000},
            {"id": "v3", "name": "Specialty Coffee Roasters", "categories": ["premium_dining"], "rating": 4.7, "userRatingCount": 8000},
            {"id": "v4", "name": "Cult Fit Gym", "categories": ["premium_retail"], "rating": 4.6, "userRatingCount": 3000},
            {"id": "v5", "name": "IT Executive PG Hostel", "categories": ["mass_services"], "rating": 3.8, "userRatingCount": 300},
            {"id": "v6", "name": "General Mall", "categories": ["general_commercial"], "rating": 4.4, "userRatingCount": 30000},
        ]
        result = self.analyzer.analyze(venues=venues, pincode="500081", area="Madhapur")
        self.assertEqual(result["classification"]["tier"], "Tier 2")
        self.assertGreaterEqual(result["scores"]["review_volume_score"], 70.0)

    def test_tier3_classification(self):
        # Sample venues representing Kukatpally / Dense Student & Coaching Corridor
        venues = [
            {"id": "v1", "name": "Sri Chaitanya Coaching", "categories": ["mass_services"], "rating": 3.9, "userRatingCount": 1200},
            {"id": "v2", "name": "Narayana Academy", "categories": ["mass_services"], "rating": 3.8, "userRatingCount": 1100},
            {"id": "v3", "name": "Royal PG Hostel", "categories": ["mass_services"], "rating": 3.7, "userRatingCount": 450},
            {"id": "v4", "name": "Babai Hotel Tiffins", "categories": ["budget_dining"], "rating": 4.3, "userRatingCount": 5400},
            {"id": "v5", "name": "Andhra Meals Mess", "categories": ["budget_dining"], "rating": 4.1, "userRatingCount": 3200},
            {"id": "v6", "name": "Supermarket Retail", "categories": ["general_commercial"], "rating": 4.2, "userRatingCount": 4000},
            {"id": "v7", "name": "General Commercial Store", "categories": ["general_commercial"], "rating": 4.0, "userRatingCount": 2000},
            {"id": "v8", "name": "Local Retail Mall", "categories": ["general_commercial"], "rating": 4.2, "userRatingCount": 15000},
        ]
        result = self.analyzer.analyze(venues=venues, pincode="500072", area="Kukatpally")
        self.assertEqual(result["classification"]["tier"], "Tier 3")
        self.assertGreaterEqual(result["scores"]["mass_density_pct"], 30.0)

    def test_tier4_classification(self):
        # Sample venues representing Medchal / Peripheral Corridor
        venues = [
            {"id": "v1", "name": "Highway Dhaba", "categories": ["budget_dining"], "rating": 3.9, "userRatingCount": 200},
            {"id": "v2", "name": "Village Kirana Store", "categories": ["general_commercial"], "rating": 4.0, "userRatingCount": 100},
            {"id": "v3", "name": "Tractor Repair Garage", "categories": ["general_commercial"], "rating": 3.8, "userRatingCount": 50},
        ]
        result = self.analyzer.analyze(venues=venues, pincode="501401", area="Medchal")
        self.assertEqual(result["classification"]["tier"], "Tier 4")


if __name__ == "__main__":
    unittest.main()

