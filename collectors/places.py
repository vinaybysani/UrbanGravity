"""
collectors/places.py - UrbanGravity spatial places data collector.
Handles geocoding, Google Places API (New) spatial radius queries, deduplication, field extraction,
and realistic Hyderabad micro-market benchmark datasets.
"""

import json
import logging
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

# Optional imports with standard library fallbacks
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

from config import (
    GOOGLE_API_KEY,
    PLACES_NEW_SEARCH_URL,
    GEOCODING_API_URL,
    PLACES_FIELD_MASK,
    DEFAULT_SEARCH_RADIUS_METERS,
    HYDERABAD_CENTROID,
    CATEGORY_BUCKETS,
    HYDERABAD_PINCODE_BENCHMARKS
)

logger = logging.getLogger(__name__)


class PlacesCollector:
    """
    Collects commercial venue data from Google Places API (New)
    or generates realistic benchmark data for offline evaluation.
    """

    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        self.api_key = api_key or GOOGLE_API_KEY
        self.use_mock = use_mock or not bool(self.api_key)

        if not self.api_key and not use_mock:
            logger.warning("No GOOGLE_API_KEY provided. Defaulting to mock dataset mode.")
            self.use_mock = True

    def _http_post_json(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Performs HTTP POST request returning JSON, using requests or urllib."""
        if HAS_REQUESTS:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            return resp.json()
        else:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def _http_get_json(self, url: str) -> Dict[str, Any]:
        """Performs HTTP GET request returning JSON, using requests or urllib."""
        if HAS_REQUESTS:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        else:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def geocode_target(self, pincode: Optional[str] = None, area: Optional[str] = None) -> Tuple[float, float, str]:
        """
        Geocodes a PIN code or Area Name to Hyderabad coordinates (latitude, longitude)
        and returns resolved formatted address/label.
        """
        # 1. Check local Hyderabad benchmark dictionary first for exact match
        pincode_str = str(pincode).strip() if pincode else ""
        area_str = str(area).strip() if area else ""

        if pincode_str and pincode_str in HYDERABAD_PINCODE_BENCHMARKS:
            bench = HYDERABAD_PINCODE_BENCHMARKS[pincode_str]
            resolved_name = f"{bench['area_name']} (PIN {pincode_str}), Hyderabad"
            return bench["lat"], bench["lng"], resolved_name

        if area_str:
            area_lower = area_str.lower()
            for code, bench in HYDERABAD_PINCODE_BENCHMARKS.items():
                if area_lower in bench["area_name"].lower() or bench["area_name"].lower() in area_lower:
                    resolved_name = f"{bench['area_name']} (PIN {code}), Hyderabad"
                    return bench["lat"], bench["lng"], resolved_name

        # 2. If running mock mode, use Hyderabad center or approximate coordinates
        if self.use_mock:
            resolved_label = f"{area_str or 'Micro-market'} (PIN: {pincode_str or 'Generic'}), Hyderabad"
            return HYDERABAD_CENTROID["latitude"], HYDERABAD_CENTROID["longitude"], resolved_label

        # 3. Live Geocoding via Google Geocoding API
        query_parts = []
        if area_str:
            query_parts.append(area_str)
        if pincode_str:
            query_parts.append(pincode_str)
        query_parts.extend(["Hyderabad", "Telangana", "India"])
        full_address = ", ".join(query_parts)

        params = urllib.parse.urlencode({
            "address": full_address,
            "key": self.api_key
        })
        url = f"{GEOCODING_API_URL}?{params}"

        try:
            data = self._http_get_json(url)
            if data.get("status") == "OK" and data.get("results"):
                first_res = data["results"][0]
                lat = first_res["geometry"]["location"]["lat"]
                lng = first_res["geometry"]["location"]["lng"]
                fmt_addr = first_res.get("formatted_address", full_address)
                return float(lat), float(lng), fmt_addr
        except Exception as e:
            logger.warning(f"Geocoding API call failed ({e}). Falling back to Hyderabad Centroid.")

        return HYDERABAD_CENTROID["latitude"], HYDERABAD_CENTROID["longitude"], full_address

    def query_places_new(
        self,
        query: str,
        lat: float,
        lng: float,
        radius: int = DEFAULT_SEARCH_RADIUS_METERS
    ) -> List[Dict[str, Any]]:
        """
        Executes a spatial search query against Google Places API (New) searchText endpoint.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": PLACES_FIELD_MASK
        }

        payload = {
            "textQuery": f"{query} in Hyderabad",
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lng
                    },
                    "radius": float(radius)
                }
            },
            "maxResultCount": 20
        }

        try:
            res_json = self._http_post_json(PLACES_NEW_SEARCH_URL, headers=headers, payload=payload)
            raw_places = res_json.get("places", [])
            extracted = []
            for p in raw_places:
                loc = p.get("location", {})
                extracted.append({
                    "id": p.get("id", ""),
                    "name": p.get("displayName", {}).get("text", "Unknown"),
                    "primaryType": p.get("primaryType", ""),
                    "types": p.get("types", []),
                    "rating": float(p.get("rating", 0.0) or 0.0),
                    "userRatingCount": int(p.get("userRatingCount", 0) or 0),
                    "formattedAddress": p.get("formattedAddress", ""),
                    "latitude": float(loc.get("latitude", 0.0) or 0.0),
                    "longitude": float(loc.get("longitude", 0.0) or 0.0),
                })
            return extracted
        except Exception as e:
            logger.error(f"Error querying Places API for '{query}': {e}")
            return []

    def collect_all_categories(
        self,
        lat: float,
        lng: float,
        radius: int = DEFAULT_SEARCH_RADIUS_METERS,
        pincode: Optional[str] = None,
        area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates queries across all category buckets and deduplicates results.
        Returns a dict containing:
          - 'venues': list of deduplicated venues with category assignments
          - 'bucket_results': mapping of bucket_id -> count & venue names
        """
        if self.use_mock:
            return self._generate_mock_data(lat, lng, pincode, area)

        unique_venues: Dict[str, Dict[str, Any]] = {}
        bucket_results: Dict[str, Dict[str, Any]] = {}

        for bucket_id, bucket_meta in CATEGORY_BUCKETS.items():
            bucket_venues = []
            queries = bucket_meta["queries"]
            for q in queries:
                places = self.query_places_new(q, lat, lng, radius)
                for p in places:
                    p_id = p["id"]
                    if not p_id:
                        p_id = f"{p['name']}_{p['latitude']}_{p['longitude']}"
                    
                    if p_id not in unique_venues:
                        p_copy = dict(p)
                        p_copy["categories"] = [bucket_id]
                        p_copy["matched_queries"] = [q]
                        unique_venues[p_id] = p_copy
                    else:
                        if bucket_id not in unique_venues[p_id]["categories"]:
                            unique_venues[p_id]["categories"].append(bucket_id)
                        if q not in unique_venues[p_id]["matched_queries"]:
                            unique_venues[p_id]["matched_queries"].append(q)
                    bucket_venues.append(unique_venues[p_id])

            bucket_results[bucket_id] = {
                "display_name": bucket_meta["display_name"],
                "count": len(bucket_venues),
                "is_premium": bucket_meta["is_premium"],
                "venues": [v["name"] for v in bucket_venues[:5]]  # Top 5 sample
            }

        return {
            "venues": list(unique_venues.values()),
            "bucket_results": bucket_results,
            "is_mock": False
        }

    def _generate_mock_data(
        self,
        lat: float,
        lng: float,
        pincode: Optional[str],
        area: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generates realistic, curated commercial footprints for Hyderabad PIN codes
        representing Tier 1 (Banjara/Jubilee Hills), Tier 2 (Madhapur/Hitec City),
        Tier 3 (Kukatpally/Dilsukhnagar), or Tier 4 (Medchal/Patancheru).
        """
        pincode_clean = str(pincode).strip() if pincode else ""
        area_clean = str(area).strip().lower() if area else ""

        # Archetype selection based on PIN / Area
        if pincode_clean in ["500034", "500033", "500096"] or any(k in area_clean for k in ["banjara", "jubilee", "film"]):
            archetype = "tier1_banjara"
        elif pincode_clean in ["500081", "500032", "500075", "500084"] or any(k in area_clean for k in ["madhapur", "gachibowli", "hitec", "financial", "kondapur"]):
            archetype = "tier2_madhapur"
        elif pincode_clean in ["500072", "500060", "500016"] or any(k in area_clean for k in ["kukatpally", "dilsukhnagar", "ameerpet", "kphb"]):
            archetype = "tier3_kukatpally"
        else:
            archetype = "tier4_peripheral"

        venues = []

        if archetype == "tier1_banjara":
            venues = [
                # Luxury Automotive
                {"id": "bj_l1", "name": "Porsche Centre Hyderabad", "primaryType": "car_dealer", "rating": 4.8, "userRatingCount": 420, "formattedAddress": "Road No. 2, Banjara Hills, Hyderabad", "latitude": 17.4190, "longitude": 78.4380, "categories": ["luxury_automotive"], "matched_queries": ["Porsche"]},
                {"id": "bj_l2", "name": "BMW KUN Exclusive Showroom", "primaryType": "car_dealer", "rating": 4.6, "userRatingCount": 1150, "formattedAddress": "Road No. 3, Banjara Hills, Hyderabad", "latitude": 17.4210, "longitude": 78.4350, "categories": ["luxury_automotive"], "matched_queries": ["BMW"]},
                {"id": "bj_l3", "name": "Mercedes-Benz Silver Star", "primaryType": "car_dealer", "rating": 4.7, "userRatingCount": 980, "formattedAddress": "Road No. 36, Jubilee Hills, Hyderabad", "latitude": 17.4320, "longitude": 78.4090, "categories": ["luxury_automotive"], "matched_queries": ["Mercedes-Benz"]},
                {"id": "bj_l4", "name": "Audi Hyderabad", "primaryType": "car_dealer", "rating": 4.5, "userRatingCount": 870, "formattedAddress": "Road No. 12, Banjara Hills, Hyderabad", "latitude": 17.4130, "longitude": 78.4410, "categories": ["luxury_automotive"], "matched_queries": ["Audi"]},
                {"id": "bj_l5", "name": "Jaguar Land Rover Pride Motors", "primaryType": "car_dealer", "rating": 4.6, "userRatingCount": 610, "formattedAddress": "Banjara Hills Main Rd, Hyderabad", "latitude": 17.4160, "longitude": 78.4440, "categories": ["luxury_automotive"], "matched_queries": ["Jaguar", "Land Rover"]},
                
                # Dining & Social Hubs
                {"id": "bj_d1", "name": "Roastery Coffee House", "primaryType": "cafe", "rating": 4.7, "userRatingCount": 12800, "formattedAddress": "Road No. 14, Banjara Hills, Hyderabad", "latitude": 17.4140, "longitude": 78.4390, "categories": ["premium_dining"], "matched_queries": ["specialty coffee"]},
                {"id": "bj_d2", "name": "Sanctuary Bar & Kitchen", "primaryType": "fine_dining_restaurant", "rating": 4.5, "userRatingCount": 4900, "formattedAddress": "Road No. 1, Banjara Hills, Hyderabad", "latitude": 17.4240, "longitude": 78.4480, "categories": ["premium_dining"], "matched_queries": ["fine dining", "restobar"]},
                {"id": "bj_d3", "name": "Farzi Cafe Hyderabad", "primaryType": "restaurant", "rating": 4.4, "userRatingCount": 7300, "formattedAddress": "Road No. 36, Jubilee Hills, Hyderabad", "latitude": 17.4310, "longitude": 78.4060, "categories": ["premium_dining"], "matched_queries": ["fine dining"]},
                {"id": "bj_d4", "name": "Conçu Pâtisserie & Cafe", "primaryType": "bakery", "rating": 4.6, "userRatingCount": 8900, "formattedAddress": "Road No. 37, Jubilee Hills, Hyderabad", "latitude": 17.4330, "longitude": 78.4010, "categories": ["premium_dining"], "matched_queries": ["specialty coffee"]},
                {"id": "bj_d5", "name": "Prost Craft Brewery", "primaryType": "brewery", "rating": 4.5, "userRatingCount": 11200, "formattedAddress": "Road No. 45, Jubilee Hills, Hyderabad", "latitude": 17.4380, "longitude": 78.4040, "categories": ["premium_dining"], "matched_queries": ["microbrewery"]},
                
                # Retail & Wellness Anchors
                {"id": "bj_r1", "name": "Q-Mart Gourmet Supermarket", "primaryType": "grocery_store", "rating": 4.6, "userRatingCount": 3500, "formattedAddress": "Road No. 2, Banjara Hills, Hyderabad", "latitude": 17.4180, "longitude": 78.4360, "categories": ["premium_retail"], "matched_queries": ["gourmet supermarket"]},
                {"id": "bj_r2", "name": "Nature's Basket Artisan Pantry", "primaryType": "grocery_store", "rating": 4.4, "userRatingCount": 1600, "formattedAddress": "Road No. 36, Jubilee Hills, Hyderabad", "latitude": 17.4300, "longitude": 78.4080, "categories": ["premium_retail"], "matched_queries": ["organic store"]},
                {"id": "bj_r3", "name": "F45 Training Jubilee Hills", "primaryType": "gym", "rating": 4.9, "userRatingCount": 320, "formattedAddress": "Road No. 10, Jubilee Hills, Hyderabad", "latitude": 17.4260, "longitude": 78.4150, "categories": ["premium_retail"], "matched_queries": ["boutique gym"]},
                {"id": "bj_r4", "name": "The Pilates Studio Hyderabad", "primaryType": "gym", "rating": 4.8, "userRatingCount": 180, "formattedAddress": "Road No. 12, Banjara Hills, Hyderabad", "latitude": 17.4120, "longitude": 78.4430, "categories": ["premium_retail"], "matched_queries": ["pilates studio"]},

                # Baseline / Budget Anchors (Low density in Banjara)
                {"id": "bj_b1", "name": "Minerva Coffee Shop (Banjara)", "primaryType": "restaurant", "rating": 4.2, "userRatingCount": 4200, "formattedAddress": "Road No. 3, Banjara Hills, Hyderabad", "latitude": 17.4220, "longitude": 78.4390, "categories": ["budget_dining"], "matched_queries": ["tiffin center"]},
                {"id": "bj_g1", "name": "GVK One Mall", "primaryType": "shopping_mall", "rating": 4.4, "userRatingCount": 24000, "formattedAddress": "Road No. 1, Banjara Hills, Hyderabad", "latitude": 17.4230, "longitude": 78.4510, "categories": ["general_commercial"], "matched_queries": ["shopping center"]},
                {"id": "bj_g2", "name": "HDFC Bank Private Banking Branch", "primaryType": "bank", "rating": 4.1, "userRatingCount": 310, "formattedAddress": "Road No. 10, Banjara Hills, Hyderabad", "latitude": 17.4170, "longitude": 78.4320, "categories": ["general_commercial"], "matched_queries": ["bank"]},
            ]

        elif archetype == "tier2_madhapur":
            venues = [
                # Automotive (Mass/Commercial Dealership)
                {"id": "md_l1", "name": "PPS Hyundai Showroom Madhapur", "primaryType": "car_dealer", "rating": 4.2, "userRatingCount": 1150, "formattedAddress": "Hitec City Rd, Madhapur, Hyderabad", "latitude": 17.4420, "longitude": 78.3610, "categories": ["general_commercial"], "matched_queries": ["car dealership"]},
                
                # Dining & Social Hubs (Very High Density: Breweries & Third Wave Cafes)
                {"id": "md_d1", "name": "Broadway The Brewery", "primaryType": "brewery", "rating": 4.7, "userRatingCount": 18500, "formattedAddress": "Jubilee Hills / Madhapur Rd, Hyderabad", "latitude": 17.4390, "longitude": 78.3980, "categories": ["premium_dining"], "matched_queries": ["microbrewery"]},
                {"id": "md_d2", "name": "Zero40 Brewing", "primaryType": "brewery", "rating": 4.6, "userRatingCount": 14200, "formattedAddress": "Financial District / Gachibowli, Hyderabad", "latitude": 17.4180, "longitude": 78.3420, "categories": ["premium_dining"], "matched_queries": ["microbrewery"]},
                {"id": "md_d3", "name": "Ironhill Brewery Hyderabad", "primaryType": "brewery", "rating": 4.5, "userRatingCount": 16900, "formattedAddress": "VIP Hills, Madhapur, Hyderabad", "latitude": 17.4450, "longitude": 78.3880, "categories": ["premium_dining"], "matched_queries": ["microbrewery"]},
                {"id": "md_d4", "name": "Blue Tokai Coffee Roasters", "primaryType": "cafe", "rating": 4.6, "userRatingCount": 3400, "formattedAddress": "Inorbit Mall Rd, Madhapur, Hyderabad", "latitude": 17.4360, "longitude": 78.3860, "categories": ["premium_dining"], "matched_queries": ["specialty coffee"]},
                {"id": "md_d5", "name": "Third Wave Coffee Hitec City", "primaryType": "cafe", "rating": 4.5, "userRatingCount": 4200, "formattedAddress": "Cyber Towers, Hitec City, Hyderabad", "latitude": 17.4500, "longitude": 78.3810, "categories": ["premium_dining"], "matched_queries": ["specialty coffee", "third wave coffee"]},
                {"id": "md_d6", "name": "Roast CCX Specialty Cafe", "primaryType": "cafe", "rating": 4.6, "userRatingCount": 2900, "formattedAddress": "Kavuri Hills, Madhapur, Hyderabad", "latitude": 17.4430, "longitude": 78.3950, "categories": ["premium_dining"], "matched_queries": ["specialty coffee"]},
                {"id": "md_d7", "name": "Forge Breu-Hous", "primaryType": "brewery", "rating": 4.4, "userRatingCount": 6800, "formattedAddress": "Hitec City Main Rd, Hyderabad", "latitude": 17.4470, "longitude": 78.3840, "categories": ["premium_dining"], "matched_queries": ["microbrewery", "restobar"]},

                # Retail & Wellness Anchors
                {"id": "md_r1", "name": "Cult.fit Madhapur Elite", "primaryType": "gym", "rating": 4.7, "userRatingCount": 2400, "formattedAddress": "Ayyappa Society, Madhapur, Hyderabad", "latitude": 17.4490, "longitude": 78.3910, "categories": ["premium_retail"], "matched_queries": ["boutique gym"]},
                {"id": "md_r2", "name": "Ratnadeep Supermarket Gourmet", "primaryType": "supermarket", "rating": 4.4, "userRatingCount": 5100, "formattedAddress": "Madhapur 100ft Rd, Hyderabad", "latitude": 17.4460, "longitude": 78.3930, "categories": ["premium_retail"], "matched_queries": ["gourmet supermarket"]},
                {"id": "md_r3", "name": "Organic India Wellness Store", "primaryType": "health_food_store", "rating": 4.3, "userRatingCount": 450, "formattedAddress": "Hitec City, Hyderabad", "latitude": 17.4480, "longitude": 78.3850, "categories": ["premium_retail"], "matched_queries": ["organic store"]},

                # Mixed / Mass Anchors (Tech PG Hostels & Quick Tiffins)
                {"id": "md_m1", "name": "Varalakshmi Tiffins Madhapur", "primaryType": "restaurant", "rating": 4.1, "userRatingCount": 8900, "formattedAddress": "Madhapur Main Rd, Hyderabad", "latitude": 17.4460, "longitude": 78.3900, "categories": ["budget_dining"], "matched_queries": ["tiffin center"]},
                {"id": "md_m2", "name": "Sri Sai Luxury Executive PG For Men", "primaryType": "lodging", "rating": 3.8, "userRatingCount": 340, "formattedAddress": "Ayyappa Society, Madhapur, Hyderabad", "latitude": 17.4520, "longitude": 78.3940, "categories": ["mass_services"], "matched_queries": ["pg hostel"]},
                {"id": "md_g1", "name": "Inorbit Mall Cyberabad", "primaryType": "shopping_mall", "rating": 4.5, "userRatingCount": 38000, "formattedAddress": "Mindspace, Madhapur, Hyderabad", "latitude": 17.4340, "longitude": 78.3870, "categories": ["general_commercial"], "matched_queries": ["shopping center"]},
            ]

        elif archetype == "tier3_kukatpally":
            venues = [
                # Luxury Automotive (Zero luxury flagships; mass dealerships)
                {"id": "kp_l1", "name": "Maruti Suzuki Arena Kukatpally", "primaryType": "car_dealer", "rating": 4.3, "userRatingCount": 2100, "formattedAddress": "KPHB Colony Main Rd, Hyderabad", "latitude": 17.4920, "longitude": 78.4040, "categories": ["general_commercial"], "matched_queries": ["car dealership"]},
                {"id": "kp_l2", "name": "Hyundai Kun United Kukatpally", "primaryType": "car_dealer", "rating": 4.2, "userRatingCount": 1850, "formattedAddress": "NH65, Kukatpally, Hyderabad", "latitude": 17.4890, "longitude": 78.4110, "categories": ["general_commercial"], "matched_queries": ["car dealership"]},

                # Dining (Mass tiffins, mess, family restaurants)
                {"id": "kp_d1", "name": "Chutneys Kukatpally", "primaryType": "restaurant", "rating": 4.1, "userRatingCount": 6700, "formattedAddress": "KPHB Phase 1, Hyderabad", "latitude": 17.4940, "longitude": 78.4020, "categories": ["budget_dining"], "matched_queries": ["tiffin center"]},
                {"id": "kp_d2", "name": "Babai Hotel Authentic Tiffins", "primaryType": "restaurant", "rating": 4.3, "userRatingCount": 5400, "formattedAddress": "Road No. 1, KPHB Colony, Hyderabad", "latitude": 17.4950, "longitude": 78.3990, "categories": ["budget_dining"], "matched_queries": ["tiffin center"]},
                {"id": "kp_d3", "name": "Kakatiya Deluxe Mess", "primaryType": "restaurant", "rating": 4.2, "userRatingCount": 3900, "formattedAddress": "Kukatpally Y Junction, Hyderabad", "latitude": 17.4870, "longitude": 78.4150, "categories": ["budget_dining"], "matched_queries": ["andhra mess"]},
                {"id": "kp_d4", "name": "Pista House Kukatpally", "primaryType": "restaurant", "rating": 4.2, "userRatingCount": 11500, "formattedAddress": "KPHB Main Rd, Hyderabad", "latitude": 17.4910, "longitude": 78.4030, "categories": ["general_commercial"], "matched_queries": ["restaurant"]},
                {"id": "kp_d5", "name": "Chai Point KPHB", "primaryType": "cafe", "rating": 4.0, "userRatingCount": 1200, "formattedAddress": "Manjeera Mall Rd, Kukatpally, Hyderabad", "latitude": 17.4900, "longitude": 78.3950, "categories": ["premium_dining"], "matched_queries": ["specialty coffee"]},

                # High Density Student & Coaching Anchors
                {"id": "kp_m1", "name": "Sri Chaitanya IIT Academy Kukatpally", "primaryType": "educational_institution", "rating": 3.9, "userRatingCount": 1450, "formattedAddress": "KPHB Colony Phase 3, Hyderabad", "latitude": 17.4970, "longitude": 78.3980, "categories": ["mass_services"], "matched_queries": ["coaching center"]},
                {"id": "kp_m2", "name": "Narayana Educational Institutions", "primaryType": "educational_institution", "rating": 3.8, "userRatingCount": 1120, "formattedAddress": "Kukatpally Housing Board, Hyderabad", "latitude": 17.4930, "longitude": 78.4000, "categories": ["mass_services"], "matched_queries": ["coaching center"]},
                {"id": "kp_m3", "name": "Sri Sai Mens PG Hostel & Mess", "primaryType": "lodging", "rating": 3.7, "userRatingCount": 490, "formattedAddress": "Road No. 4, KPHB Colony, Hyderabad", "latitude": 17.4960, "longitude": 78.3960, "categories": ["mass_services"], "matched_queries": ["pg hostel", "men's hostel"]},
                {"id": "kp_m4", "name": "Venkateshwara Deluxe Mens Hostel", "primaryType": "lodging", "rating": 3.6, "userRatingCount": 380, "formattedAddress": "KPHB Phase 1, Hyderabad", "latitude": 17.4950, "longitude": 78.4010, "categories": ["mass_services"], "matched_queries": ["men's hostel"]},
                
                # Retail
                {"id": "kp_r1", "name": "Vijetha Supermarket Kukatpally", "primaryType": "supermarket", "rating": 4.2, "userRatingCount": 4800, "formattedAddress": "KPHB Colony Main Rd, Hyderabad", "latitude": 17.4930, "longitude": 78.4050, "categories": ["general_commercial"], "matched_queries": ["supermarket"]},
                {"id": "kp_r2", "name": "DMart Kukatpally", "primaryType": "hypermarket", "rating": 4.3, "userRatingCount": 18200, "formattedAddress": "NH65, Kukatpally, Hyderabad", "latitude": 17.4880, "longitude": 78.4120, "categories": ["general_commercial"], "matched_queries": ["shopping center"]},
                {"id": "kp_r3", "name": "Manjeera Trinity Mall", "primaryType": "shopping_mall", "rating": 4.2, "userRatingCount": 15400, "formattedAddress": "JNTU Rd, Kukatpally, Hyderabad", "latitude": 17.4900, "longitude": 78.3940, "categories": ["general_commercial"], "matched_queries": ["shopping center"]},
            ]

        else:  # tier4_peripheral
            venues = [
                {"id": "p_b1", "name": "Balaram Tiffin Center", "primaryType": "restaurant", "rating": 4.1, "userRatingCount": 380, "formattedAddress": "Medchal Highway, Hyderabad", "latitude": 17.6250, "longitude": 78.4820, "categories": ["budget_dining"], "matched_queries": ["tiffin center"]},
                {"id": "p_b2", "name": "Srinivasa Andhra Meals & Mess", "primaryType": "restaurant", "rating": 3.9, "userRatingCount": 210, "formattedAddress": "Main Road, Medchal, Hyderabad", "latitude": 17.6280, "longitude": 78.4800, "categories": ["budget_dining"], "matched_queries": ["andhra mess"]},
                {"id": "p_g1", "name": "Sri Lakshmi Kirana & General Stores", "primaryType": "grocery_store", "rating": 4.0, "userRatingCount": 140, "formattedAddress": "Medchal Bazaar, Hyderabad", "latitude": 17.6300, "longitude": 78.4810, "categories": ["general_commercial"], "matched_queries": ["supermarket"]},
                {"id": "p_g2", "name": "State Bank of India Medchal Branch", "primaryType": "bank", "rating": 3.8, "userRatingCount": 420, "formattedAddress": "National Highway 44, Hyderabad", "latitude": 17.6290, "longitude": 78.4830, "categories": ["general_commercial"], "matched_queries": ["bank"]},
                {"id": "p_m1", "name": "Medchal Auto Works & Garage", "primaryType": "car_repair", "rating": 4.2, "userRatingCount": 95, "formattedAddress": "Industrial Area, Medchal, Hyderabad", "latitude": 17.6310, "longitude": 78.4850, "categories": ["general_commercial"], "matched_queries": ["auto repair"]},
            ]

        # Calculate bucket results from venues
        bucket_results = {}
        for b_id, b_meta in CATEGORY_BUCKETS.items():
            matching = [v for v in venues if b_id in v.get("categories", [])]
            bucket_results[b_id] = {
                "display_name": b_meta["display_name"],
                "count": len(matching),
                "is_premium": b_meta["is_premium"],
                "venues": [v["name"] for v in matching[:5]]
            }

        return {
            "venues": venues,
            "bucket_results": bucket_results,
            "is_mock": True
        }
