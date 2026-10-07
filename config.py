"""
config.py - Configuration module for UrbanGravity (Geospatial Real Estate Intelligence Platform).
Defines Google Places API (New) endpoints, category query buckets, scoring weights,
and Indian real-estate benchmarks for Hyderabad micro-markets.
"""

import os

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Lightweight fallback parser for .env if python-dotenv is not installed
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        except Exception:
            pass

# Google Places API (New) Settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PLACES_NEW_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Fields to retrieve via Places API (New) FieldMask
PLACES_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.primaryType,"
    "places.types,"
    "places.rating,"
    "places.userRatingCount,"
    "places.formattedAddress,"
    "places.location"
)

# Spatial Parameters (Hyderabad metro region)
DEFAULT_SEARCH_RADIUS_METERS = 4000  # 4km default (within 3km - 5km requirement)
CACHE_DIR = os.getenv("URBANGRAVITY_CACHE_DIR", os.path.join(os.path.dirname(__file__), "data", "cache"))
HYDERABAD_CENTROID = {
    "latitude": 17.3850,
    "longitude": 78.4867
}

# ==============================================================================
# Category Buckets & Search Queries
# ==============================================================================

# a) Luxury Automotive: High discretionary spending marquee brands
LUXURY_AUTOMOTIVE_BRANDS = [
    "Porsche",
    "BMW",
    "Mercedes-Benz",
    "Audi",
    "Lexus",
    "Jaguar",
    "Land Rover"
]

# Baseline automotive to contrast luxury vs general
GENERAL_AUTOMOTIVE_QUERIES = [
    "car dealership",
    "used car showroom",
    "auto repair"
]

# b) Dining & Social Hubs: Lifestyle spending vs budget staples
PREMIUM_DINING_QUERIES = [
    "microbrewery",
    "specialty coffee",
    "third wave coffee",
    "fine dining",
    "restobar",
    "gourmet bakery"
]

BUDGET_DINING_QUERIES = [
    "tiffin center",
    "andhra mess",
    "meals mess",
    "tea stall"
]

# c) Retail & Wellness Anchors: Modern affluent consumption vs mass services
PREMIUM_RETAIL_QUERIES = [
    "gourmet supermarket",
    "organic store",
    "boutique gym",
    "pilates studio",
    "luxury salon"
]

MASS_SERVICES_QUERIES = [
    "coaching center",
    "pg hostel",
    "men's hostel",
    "women's hostel",
    "government school"
]

# Baseline commercial queries to estimate total commercial activity
BASELINE_COMMERCIAL_QUERIES = [
    "shopping center",
    "supermarket",
    "restaurant",
    "bank",
    "pharmacy"
]

# Category Bucket Groupings for Analysis
CATEGORY_BUCKETS = {
    "luxury_automotive": {
        "display_name": "Luxury Automotive Showrooms",
        "queries": LUXURY_AUTOMOTIVE_BRANDS,
        "is_premium": True,
        "weight": 25.0
    },
    "premium_dining": {
        "display_name": "Breweries & Specialty Dining",
        "queries": PREMIUM_DINING_QUERIES,
        "is_premium": True,
        "weight": 10.0
    },
    "premium_retail": {
        "display_name": "Gourmet Retail & Boutique Wellness",
        "queries": PREMIUM_RETAIL_QUERIES,
        "is_premium": True,
        "weight": 8.0
    },
    "budget_dining": {
        "display_name": "Budget Tiffins & Mess",
        "queries": BUDGET_DINING_QUERIES,
        "is_premium": False,
        "weight": -5.0
    },
    "mass_services": {
        "display_name": "Hostels & Coaching Institutes",
        "queries": MASS_SERVICES_QUERIES,
        "is_premium": False,
        "weight": -6.0
    },
    "general_commercial": {
        "display_name": "General Commercial Anchors",
        "queries": BASELINE_COMMERCIAL_QUERIES,
        "is_premium": False,
        "weight": 1.0
    }
}

# ==============================================================================
# Hyderabad Micro-Market Benchmarks (Real Estate & Cost of Living)
# ==============================================================================
HYDERABAD_PINCODE_BENCHMARKS = {
    "500034": {
        "area_name": "Banjara Hills",
        "lat": 17.4156,
        "lng": 78.4357,
        "avg_rent_sqft_inr": 80.0,
        "avg_cost_for_two_inr": 2600.0,
        "benchmark_tier": "Tier 1",
        "archetype": "Ultra-Affluent / Established Wealth"
    },
    "500033": {
        "area_name": "Jubilee Hills",
        "lat": 17.4319,
        "lng": 78.4073,
        "avg_rent_sqft_inr": 90.0,
        "avg_cost_for_two_inr": 2800.0,
        "benchmark_tier": "Tier 1",
        "archetype": "Ultra-Affluent / High Discretionary Spending"
    },
    "500096": {
        "area_name": "Film Nagar",
        "lat": 17.4172,
        "lng": 78.4116,
        "avg_rent_sqft_inr": 70.0,
        "avg_cost_for_two_inr": 2200.0,
        "benchmark_tier": "Tier 1",
        "archetype": "Affluent Arts & Media Enclave"
    },
    "500081": {
        "area_name": "Madhapur / Hitec City",
        "lat": 17.4483,
        "lng": 78.3915,
        "avg_rent_sqft_inr": 58.0,
        "avg_cost_for_two_inr": 1800.0,
        "benchmark_tier": "Tier 2",
        "archetype": "High-Growth IT / Corporate & Social Hub"
    },
    "500032": {
        "area_name": "Gachibowli",
        "lat": 17.4401,
        "lng": 78.3489,
        "avg_rent_sqft_inr": 52.0,
        "avg_cost_for_two_inr": 1600.0,
        "benchmark_tier": "Tier 2",
        "archetype": "Tech Corridor & Modern Gated Communities"
    },
    "500075": {
        "area_name": "Financial District",
        "lat": 17.4168,
        "lng": 78.3392,
        "avg_rent_sqft_inr": 55.0,
        "avg_cost_for_two_inr": 1700.0,
        "benchmark_tier": "Tier 2",
        "archetype": "Multinational BFSI & High-Rise Tech Corridor"
    },
    "500084": {
        "area_name": "Kondapur",
        "lat": 17.4646,
        "lng": 78.3585,
        "avg_rent_sqft_inr": 42.0,
        "avg_cost_for_two_inr": 1300.0,
        "benchmark_tier": "Tier 2",
        "archetype": "Upper-Middle Tech Residential"
    },
    "500072": {
        "area_name": "Kukatpally / KPHB",
        "lat": 17.4938,
        "lng": 78.4018,
        "avg_rent_sqft_inr": 28.0,
        "avg_cost_for_two_inr": 650.0,
        "benchmark_tier": "Tier 3",
        "archetype": "Dense Middle-Income Residential / Retail Corridor"
    },
    "500060": {
        "area_name": "Dilsukhnagar",
        "lat": 17.3688,
        "lng": 78.5247,
        "avg_rent_sqft_inr": 25.0,
        "avg_cost_for_two_inr": 500.0,
        "benchmark_tier": "Tier 3",
        "archetype": "High-Footfall Traditional Commercial & Educational Hub"
    },
    "500016": {
        "area_name": "Ameerpet",
        "lat": 17.4375,
        "lng": 78.4483,
        "avg_rent_sqft_inr": 32.0,
        "avg_cost_for_two_inr": 550.0,
        "benchmark_tier": "Tier 3",
        "archetype": "Dense Coaching & Student Hostel Hub"
    },
    "501401": {
        "area_name": "Medchal",
        "lat": 17.6297,
        "lng": 78.4814,
        "avg_rent_sqft_inr": 16.0,
        "avg_cost_for_two_inr": 350.0,
        "benchmark_tier": "Tier 4",
        "archetype": "Emerging / Peripheral Industrial & Price-Sensitive"
    },
    "502319": {
        "area_name": "Patancheru",
        "lat": 17.5317,
        "lng": 78.2642,
        "avg_rent_sqft_inr": 14.0,
        "avg_cost_for_two_inr": 300.0,
        "benchmark_tier": "Tier 4",
        "archetype": "Industrial Corridor / Outer Growth District"
    }
}

# ==============================================================================
# Tier Definitions & Classification Labels
# ==============================================================================
TIER_DEFINITIONS = {
    "Tier 1": {
        "title": "Tier 1: Ultra-Affluent / High Discretionary Spending",
        "description": "Dominated by luxury automotive flagships, high-end fine dining, organic grocers, and generational wealth.",
        "examples": "Banjara Hills, Jubilee Hills, Film Nagar"
    },
    "Tier 2": {
        "title": "Tier 2: High-Growth IT / Corporate Hub",
        "description": "High concentration of craft microbreweries, specialty third-wave coffee, active lifestyle brands, and high footfall.",
        "examples": "Gachibowli, Madhapur, Hitec City, Financial District"
    },
    "Tier 3": {
        "title": "Tier 3: Dense Middle-Income Residential / Retail Corridor",
        "description": "High commercial density of tiffin centers, Andhra messes, student hostels, coaching institutes, and mass-market retail.",
        "examples": "Kukatpally, Dilsukhnagar, Ameerpet, KPHB"
    },
    "Tier 4": {
        "title": "Tier 4: Emerging / Price-Sensitive District",
        "description": "Periphery micro-market with lower commercial density, localized unorganized retail, and value-focused spending.",
        "examples": "Medchal, Patancheru, Ghatkesar, Shamshabad Periphery"
    }
}
