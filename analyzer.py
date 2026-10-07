"""
analyzer.py - UrbanGravity quantitative economic intelligence & demographic tier classification engine.
Calculates Premium Density Index (PDI), Review Volume Score (RVS),
weighted Affluence Score (0-100), and classifies micro-markets into 4 socio-economic tiers.
Includes RealEstateProxyStore for ingesting benchmark or scraped cost-of-living data.
"""

import json
import logging
import math
import os
from typing import Dict, List, Optional, Any, Tuple

from config import (
    CATEGORY_BUCKETS,
    HYDERABAD_PINCODE_BENCHMARKS,
    TIER_DEFINITIONS
)

logger = logging.getLogger(__name__)


class RealEstateProxyStore:
    """
    Manages micro-market benchmark metrics (average rent per sq ft, dining cost-for-two)
    and supports ingesting custom scraped real estate datasets (e.g., MagicBricks, 99acres, Zomato).
    """

    def __init__(self, custom_proxy_path: Optional[str] = None):
        self.benchmarks: Dict[str, Dict[str, Any]] = dict(HYDERABAD_PINCODE_BENCHMARKS)
        if custom_proxy_path and os.path.exists(custom_proxy_path):
            self.load_custom_proxies(custom_proxy_path)

    def load_custom_proxies(self, file_path: str) -> None:
        """Loads custom scraped JSON or CSV proxy data into the benchmark registry."""
        try:
            if file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                    for k, v in custom_data.items():
                        self.benchmarks[str(k)] = v
                logger.info(f"Loaded {len(custom_data)} custom proxy records from {file_path}")
            elif file_path.endswith(".csv"):
                # Parse CSV with fallback
                import csv
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        pincode = row.get("pincode", "").strip()
                        if pincode:
                            self.benchmarks[pincode] = {
                                "area_name": row.get("area_name", "Unknown Area"),
                                "avg_rent_sqft_inr": float(row.get("avg_rent_sqft_inr", 30.0) or 30.0),
                                "avg_cost_for_two_inr": float(row.get("avg_cost_for_two_inr", 800.0) or 800.0),
                                "benchmark_tier": row.get("benchmark_tier", "Tier 3"),
                                "archetype": row.get("archetype", "Custom Scraped Profile")
                            }
                            count += 1
                logger.info(f"Loaded {count} custom proxy records from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load custom proxies from {file_path}: {e}")

    def get_proxy(self, pincode: Optional[str] = None, area: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves proxy data for a given PIN code or Area Name, with heuristic fallbacks."""
        pin_str = str(pincode).strip() if pincode else ""
        area_str = str(area).strip().lower() if area else ""

        # Exact PIN lookup
        if pin_str in self.benchmarks:
            return self.benchmarks[pin_str]

        # Fuzzy area name lookup
        if area_str:
            for _, data in self.benchmarks.items():
                if area_str in data["area_name"].lower() or data["area_name"].lower() in area_str:
                    return data

        # Default fallback for unknown Hyderabad micro-markets
        return {
            "area_name": area or f"PIN {pincode or 'Unknown'}",
            "avg_rent_sqft_inr": 35.0,
            "avg_cost_for_two_inr": 850.0,
            "benchmark_tier": "Tier 3",
            "archetype": "General Hyderabad Suburban Commercial District"
        }


class AffluenceAnalyzer:
    """
    Computes quantitative economic indices and classifies commercial zones
    based on Google Places data and Indian real estate proxies.
    """

    def __init__(self, proxy_store: Optional[RealEstateProxyStore] = None):
        self.proxy_store = proxy_store or RealEstateProxyStore()

    def analyze(
        self,
        venues: List[Dict[str, Any]],
        pincode: Optional[str] = None,
        area: Optional[str] = None,
        radius_meters: int = 4000
    ) -> Dict[str, Any]:
        """
        Executes full demographic tier analysis on the scraped venue dataset.
        """
        total_venues = len(venues)
        proxy_data = self.proxy_store.get_proxy(pincode=pincode, area=area)

        # 1. Bucket counts & Category categorizations
        category_counts: Dict[str, int] = {k: 0 for k in CATEGORY_BUCKETS.keys()}
        categorized_venues: Dict[str, List[Dict[str, Any]]] = {k: [] for k in CATEGORY_BUCKETS.keys()}

        total_rating_sum = 0.0
        total_review_count = 0

        for v in venues:
            rating = v.get("rating", 0.0)
            reviews = v.get("userRatingCount", 0)
            total_rating_sum += rating
            total_review_count += reviews

            venue_cats = v.get("categories", [])
            for c in venue_cats:
                if c in category_counts:
                    category_counts[c] += 1
                    categorized_venues[c].append(v)

        avg_rating = round(total_rating_sum / max(1, total_venues), 2)
        avg_reviews_per_venue = round(total_review_count / max(1, total_venues), 1)

        # 2. Extract Specific Indicator Metrics
        n_luxury_auto = category_counts.get("luxury_automotive", 0)
        n_premium_dining = category_counts.get("premium_dining", 0)
        n_premium_retail = category_counts.get("premium_retail", 0)
        
        n_budget_dining = category_counts.get("budget_dining", 0)
        n_mass_services = category_counts.get("mass_services", 0)
        n_general_commercial = category_counts.get("general_commercial", 0)

        total_premium_venues = n_luxury_auto + n_premium_dining + n_premium_retail
        total_mass_venues = n_budget_dining + n_mass_services

        # 3. Calculate Core Indices
        # Premium Density Index (PDI)
        pdi = round(total_premium_venues / max(1, total_venues), 4)

        # Mass Density Index (MDI)
        mdi = round(total_mass_venues / max(1, total_venues), 4)

        # Review Volume Score (RVS): logarithmic footfall index (0 to 100)
        # Log10(1 + R) scaled to 100 where 100,000 reviews corresponds to score of 100
        if total_review_count > 0:
            log_reviews = math.log10(1 + total_review_count)
            rvs = round(min(100.0, (log_reviews / 5.0) * 100.0), 2)
        else:
            rvs = 0.0

        # 4. Composite Affluence Score (0 to 100)
        affluence_score = self._compute_affluence_score(
            pdi=pdi,
            mdi=mdi,
            n_luxury_auto=n_luxury_auto,
            n_premium_dining=n_premium_dining,
            n_premium_retail=n_premium_retail,
            avg_rent_sqft=proxy_data["avg_rent_sqft_inr"],
            rvs=rvs
        )

        # 5. Automated Tier Classification
        tier_key, tier_reason = self._classify_tier(
            affluence_score=affluence_score,
            pdi=pdi,
            mdi=mdi,
            n_luxury_auto=n_luxury_auto,
            n_premium_dining=n_premium_dining,
            total_venues=total_venues,
            rvs=rvs,
            avg_rent_sqft=proxy_data["avg_rent_sqft_inr"]
        )

        tier_metadata = TIER_DEFINITIONS.get(tier_key, {})

        # 6. Commercial Highlights & Flags
        highlights = self._extract_commercial_highlights(
            categorized_venues=categorized_venues,
            n_luxury_auto=n_luxury_auto,
            n_premium_dining=n_premium_dining,
            n_premium_retail=n_premium_retail,
            n_mass_services=n_mass_services
        )

        return {
            "target": {
                "pincode": pincode or "N/A",
                "area_name": area or proxy_data.get("area_name", "N/A"),
                "resolved_label": proxy_data.get("area_name", "Hyderabad Micro-Market"),
                "radius_meters": radius_meters
            },
            "classification": {
                "tier": tier_key,
                "tier_title": tier_metadata.get("title", tier_key),
                "description": tier_metadata.get("description", ""),
                "classification_reason": tier_reason,
                "archetype": proxy_data.get("archetype", "Urban Corridor")
            },
            "scores": {
                "affluence_score": affluence_score,
                "premium_density_index": pdi,
                "premium_density_pct": round(pdi * 100, 1),
                "mass_density_index": mdi,
                "mass_density_pct": round(mdi * 100, 1),
                "review_volume_score": rvs,
                "total_reviews": total_review_count,
                "avg_reviews_per_venue": avg_reviews_per_venue,
                "avg_rating": avg_rating
            },
            "venue_counts": {
                "total_venues": total_venues,
                "total_premium_venues": total_premium_venues,
                "total_mass_venues": total_mass_venues,
                "luxury_automotive": n_luxury_auto,
                "premium_dining": n_premium_dining,
                "premium_retail": n_premium_retail,
                "budget_dining": n_budget_dining,
                "mass_services": n_mass_services,
                "general_commercial": n_general_commercial
            },
            "proxies": {
                "avg_rent_sqft_inr": proxy_data["avg_rent_sqft_inr"],
                "avg_cost_for_two_inr": proxy_data["avg_cost_for_two_inr"],
                "benchmark_tier": proxy_data.get("benchmark_tier", "Tier 3")
            },
            "highlights": highlights
        }

    def _compute_affluence_score(
        self,
        pdi: float,
        mdi: float,
        n_luxury_auto: int,
        n_premium_dining: int,
        n_premium_retail: int,
        avg_rent_sqft: float,
        rvs: float
    ) -> float:
        """
        Calculates normalized Affluence Score on a scale of 0 to 100.
        Incorporates luxury auto weighting, premium density, real estate rent benchmarks,
        and discounts high mass-density ratios.
        """
        score = 0.0

        # Component 1: Luxury Automotive Anchor Presence (Max 25 pts)
        # In Indian metros, luxury showrooms are exclusively present in Tier 1 / elite zones.
        if n_luxury_auto >= 3:
            score += 25.0
        elif n_luxury_auto == 2:
            score += 20.0
        elif n_luxury_auto == 1:
            score += 14.0

        # Component 2: Premium Density Ratio (Max 30 pts)
        score += min(30.0, pdi * 45.0)

        # Component 3: Dining & Social Lifestyle Hubs (Max 15 pts)
        score += min(15.0, (n_premium_dining * 2.5) + (n_premium_retail * 2.0))

        # Component 4: Real Estate Rental Benchmark (Max 20 pts)
        if avg_rent_sqft >= 75.0:
            score += 20.0
        elif avg_rent_sqft >= 50.0:
            score += 15.0
        elif avg_rent_sqft >= 30.0:
            score += 10.0
        elif avg_rent_sqft >= 20.0:
            score += 7.0
        else:
            score += 2.0

        # Component 5: Footfall / Vibrancy Bonus (Max 10 pts)
        score += min(10.0, (rvs / 100.0) * 10.0)

        # Penalty / Negative Proxy: Heavy Mass Density (Discount up to -15 pts)
        penalty = min(15.0, mdi * 25.0)
        score -= penalty

        # Clamp between 0.0 and 100.0
        return round(max(0.0, min(100.0, score)), 1)

    def _classify_tier(
        self,
        affluence_score: float,
        pdi: float,
        mdi: float,
        n_luxury_auto: int,
        n_premium_dining: int,
        total_venues: int,
        rvs: float,
        avg_rent_sqft: float
    ) -> Tuple[str, str]:
        """
        Deterministic decision tree mapping quantitative indicators to Hyderabad's 4 Tiers.
        """
        # Tier 1: Ultra-Affluent / High Discretionary Spending
        # Requirements: Presence of luxury automotive flagships (>= 2) OR (>= 1 with high rent >= 70 and affluence >= 75)
        if (n_luxury_auto >= 2 or (n_luxury_auto >= 1 and avg_rent_sqft >= 70.0)) and affluence_score >= 75.0:
            return (
                "Tier 1",
                f"Ultra-affluent discretionary spending ({affluence_score}/100) anchored by {n_luxury_auto} marquee luxury automotive showroom(s), high rental benchmarks (₹{avg_rent_sqft:.1f}/sqft), and a high Premium Density Index ({round(pdi*100, 1)}%)."
            )

        # Tier 2: High-Growth IT / Corporate Hub
        # Requirements: High concentration of craft microbreweries, specialty cafes, high footfall/review score, and moderate-to-high PDI
        if (n_premium_dining >= 3 or rvs >= 70.0) and pdi >= 0.25 and affluence_score >= 45.0:
            return (
                "Tier 2",
                f"High-growth IT/corporate lifestyle corridor with strong social vibrancy ({n_premium_dining} craft breweries/specialty cafes), massive consumer review volume ({rvs}/100), and affluence score of {affluence_score}/100."
            )

        # Tier 3: Dense Middle-Income Residential / Retail Corridor
        # Requirements: Active commercial corridor (total_venues >= 8 or rvs >= 65.0) with significant mass retail, coaching, or hostels
        if total_venues >= 8 and (mdi >= 0.15 or rvs >= 65.0 or avg_rent_sqft >= 22.0):
            return (
                "Tier 3",
                f"Dense middle-income commercial corridor with high commercial volume ({total_venues} venues, {round(mdi*100, 1)}% Mass Density Index) anchored by educational institutes, hostels, and mass retail."
            )

        # Tier 4: Emerging / Price-Sensitive District
        return (
            "Tier 4",
            f"Emerging / peripheral district characterized by lower commercial density ({total_venues} venues), minimal discretionary lifestyle anchors, and low rental rates (₹{avg_rent_sqft:.1f}/sqft)."
        )

    def _extract_commercial_highlights(
        self,
        categorized_venues: Dict[str, List[Dict[str, Any]]],
        n_luxury_auto: int,
        n_premium_dining: int,
        n_premium_retail: int,
        n_mass_services: int
    ) -> List[str]:
        """Extracts key narrative bullet points summarizing commercial anchors found."""
        highlights = []

        if n_luxury_auto > 0:
            auto_names = [v["name"] for v in categorized_venues.get("luxury_automotive", [])[:3]]
            highlights.append(f"Luxury Automotive Presence: Identified marquee showrooms ({', '.join(auto_names)}).")
        else:
            highlights.append("Luxury Automotive Presence: No marquee luxury automotive dealerships found in radius.")

        if n_premium_dining > 0:
            top_dining = sorted(categorized_venues.get("premium_dining", []), key=lambda x: x.get("userRatingCount", 0), reverse=True)
            names = [v["name"] for v in top_dining[:3]]
            highlights.append(f"Lifestyle & Craft Dining: Strong footprint with flagships such as {', '.join(names)}.")

        if n_premium_retail > 0:
            ret_names = [v["name"] for v in categorized_venues.get("premium_retail", [])[:3]]
            highlights.append(f"Gourmet & Wellness Anchors: Presence of {', '.join(ret_names)}.")

        if n_mass_services > 0:
            mass_names = [v["name"] for v in categorized_venues.get("mass_services", [])[:3]]
            highlights.append(f"Student / Budget Footprint: High concentration of coaching institutes and PG hostels ({', '.join(mass_names)}).")

        return highlights
