"""
main.py - CLI entrypoint for UrbanGravity (Geospatial Real Estate Intelligence Platform).
Orchestrates geocoding, Places API (New) spatial collection, quantitative analysis,
CSV/JSON report persistence in outputs/, and rich executive terminal summary rendering.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_SEARCH_RADIUS_METERS, GOOGLE_API_KEY
from collectors.places import PlacesCollector
from analyzer import AffluenceAnalyzer, RealEstateProxyStore


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="urbangravity",
        description="UrbanGravity - Geospatial Economic & Demographic Tier Intelligence Platform."
    )
    parser.add_argument(
        "--pincode",
        type=str,
        help="Target 6-digit Indian PIN Code (e.g., 500034, 500081, 500072)"
    )
    parser.add_argument(
        "--area",
        type=str,
        help="Target Neighborhood / Locality name (e.g., 'Banjara Hills', 'Madhapur', 'Kukatpally')"
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=DEFAULT_SEARCH_RADIUS_METERS,
        help=f"Spatial search radius in meters (default: {DEFAULT_SEARCH_RADIUS_METERS}m / 4km)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Google API Key with Places API (New) and Geocoding enabled (optional, defaults to GOOGLE_API_KEY env)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline benchmark mode using authentic Hyderabad micro-market dataset"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save generated CSV and JSON reports (default: outputs/)"
    )
    parser.add_argument(
        "--custom-proxies",
        type=str,
        help="Path to custom JSON or CSV file containing real estate rent or cost-for-two data"
    )
    parser.add_argument(
        "--refresh",
        "--no-cache",
        action="store_true",
        dest="refresh",
        help="Bypass local disk cache and force fresh live queries against Google Places API"
    )
    return parser.parse_args()


def export_reports(
    analysis_results: Dict[str, Any],
    venues: List[Dict[str, Any]],
    output_dir: str,
    file_prefix: str
) -> Dict[str, str]:
    """Saves structured JSON report and CSV venue table in output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{file_prefix}_report.json")
    csv_path = os.path.join(output_dir, f"{file_prefix}_venues.csv")

    # 1. Export JSON Report
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)

    # 2. Export CSV Venues Table
    csv_rows = []
    for v in venues:
        csv_rows.append({
            "place_id": v.get("id", ""),
            "name": v.get("name", ""),
            "primary_type": v.get("primaryType", ""),
            "rating": v.get("rating", 0.0),
            "user_ratings_count": v.get("userRatingCount", 0),
            "formatted_address": v.get("formattedAddress", ""),
            "latitude": v.get("latitude", 0.0),
            "longitude": v.get("longitude", 0.0),
            "categories": ";".join(v.get("categories", [])),
            "matched_queries": ";".join(v.get("matched_queries", []))
        })

    # Try exporting with pandas if available, otherwise use standard csv module
    try:
        import pandas as pd
        df = pd.DataFrame(csv_rows)
        df.to_csv(csv_path, index=False)
    except ImportError:
        import csv
        if csv_rows:
            fieldnames = list(csv_rows[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
        else:
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("No venues recorded.\n")

    return {"json": json_path, "csv": csv_path}


def render_terminal_summary(
    analysis: Dict[str, Any],
    file_paths: Dict[str, str],
    is_mock: bool,
    from_cache: bool = False
) -> None:
    """Renders a polished, executive terminal dashboard summarizing the evaluation."""
    t = analysis["target"]
    c = analysis["classification"]
    s = analysis["scores"]
    vc = analysis["venue_counts"]
    p = analysis["proxies"]
    highlights = analysis["highlights"]

    tier_color = {
        "Tier 1": "\033[95m",  # Magenta / Purple
        "Tier 2": "\033[94m",  # Blue
        "Tier 3": "\033[93m",  # Yellow
        "Tier 4": "\033[90m"   # Gray
    }.get(c["tier"], "\033[92m")
    reset = "\033[0m"
    bold = "\033[1m"
    cyan = "\033[96m"

    if from_cache:
        data_source_mode = "[LOCAL DISK CACHE - 0 API Calls / ₹0 Cost]"
    elif is_mock:
        data_source_mode = "[OFFLINE MOCK DATASET]"
    else:
        data_source_mode = "[LIVE GOOGLE PLACES API (NEW)]"

    print("\n" + "=" * 78)
    print(f"{bold}{cyan} URBANGRAVITY 🏙️ 🧲 // COMMERCIAL AFFLUENCE & DEMOGRAPHIC INTELLIGENCE{reset}")
    print("=" * 78)
    print(f" Target Locality    : {bold}{t['area_name']}{reset} (PIN: {t['pincode']})")
    print(f" Resolved Address   : {t['resolved_label']}")
    print(f" Spatial Radius     : {t['radius_meters']}m ({round(t['radius_meters']/1000, 1)} km)")
    print(f" Data Source Mode   : {data_source_mode}")
    print("-" * 78)

    # Classification Banner
    print(f"\n{bold}>>> DEMOGRAPHIC & ECONOMIC TIER CLASSIFICATION <<<{reset}")
    print(f" {tier_color}{bold}[ {c['tier_title']} ]{reset}")
    print(f" Archetype          : {c['archetype']}")
    print(f" Classification Note: {c['classification_reason']}")

    # Quantitative Scorecard
    print(f"\n{bold}>>> QUANTITATIVE ECONOMIC SCORECARD <<<{reset}")
    print(f" ┌──────────────────────────────────────────────┬────────────────────────┐")
    print(f" │ Metric Indicator                             │ Evaluated Value        │")
    print(f" ├──────────────────────────────────────────────┼────────────────────────┤")
    print(f" │ Affluence Score (Composite 0-100)            │ {bold}{s['affluence_score']:>6.1f} / 100{reset}        │")
    print(f" │ Premium Density Index (PDI)                  │ {s['premium_density_pct']:>6.1f}% ({s['premium_density_index']})    │")
    print(f" │ Mass / Value Density Index (MDI)             │ {s['mass_density_pct']:>6.1f}% ({s['mass_density_index']})    │")
    print(f" │ Review Volume Score (Footfall Activity 0-100)│ {s['review_volume_score']:>6.1f} / 100        │")
    print(f" │ Total User Reviews Tracked                   │ {s['total_reviews']:>10,d}            │")
    print(f" │ Average Reviews per Venue                    │ {s['avg_reviews_per_venue']:>10.1f}            │")
    print(f" │ Average Commercial Venue Rating              │ {s['avg_rating']:>6.2f} / 5.00        │")
    print(f" └──────────────────────────────────────────────┴────────────────────────┘")

    # Venue Breakdown Table
    print(f"\n{bold}>>> COMMERCIAL ANCHOR FOOTPRINT COMPOSITION <<<{reset}")
    print(f" ┌──────────────────────────────────────────────┬─────────────┬──────────┐")
    print(f" │ Commercial Category Bucket                   │ Count       │ Ratio    │")
    print(f" ├──────────────────────────────────────────────┼─────────────┼──────────┤")
    print(f" │ Luxury Automotive Flagships (Porsche/BMW/etc)│ {vc['luxury_automotive']:>6d}      │ {round(vc['luxury_automotive']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" │ Breweries, Specialty Coffee & Fine Dining    │ {vc['premium_dining']:>6d}      │ {round(vc['premium_dining']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" │ Gourmet Grocers & Boutique Wellness          │ {vc['premium_retail']:>6d}      │ {round(vc['premium_retail']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" │ Budget Tiffin Centers & Andhra Messes        │ {vc['budget_dining']:>6d}      │ {round(vc['budget_dining']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" │ Student Hostels & Coaching Institutes        │ {vc['mass_services']:>6d}      │ {round(vc['mass_services']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" │ General Commercial & Baseline Retail         │ {vc['general_commercial']:>6d}      │ {round(vc['general_commercial']/max(1, vc['total_venues'])*100, 1):>6.1f}%  │")
    print(f" ├──────────────────────────────────────────────┼─────────────┼──────────┤")
    print(f" │ TOTAL UNIQUE COMMERCIAL VENUES SCRAPED       │ {bold}{vc['total_venues']:>6d}{reset}      │ 100.0%   │")
    print(f" └──────────────────────────────────────────────┴─────────────┴──────────┘")

    # Real Estate Cost-of-Living Proxies
    print(f"\n{bold}>>> HYDERABAD REAL ESTATE & COST-OF-LIVING BENCHMARKS <<<{reset}")
    print(f" • Average Commercial/Residential Rent : ₹{p['avg_rent_sqft_inr']:.1f} / sq. ft / month")
    print(f" • Average Dining Cost-for-Two         : ₹{p['avg_cost_for_two_inr']:,.0f}")
    print(f" • Micro-market Historical Benchmark   : {p['benchmark_tier']}")

    # Highlights
    print(f"\n{bold}>>> COMMERCIAL HIGHLIGHTS & KEY ANCHORS <<<{reset}")
    for h in highlights:
        print(f" • {h}")

    # Output Files
    print(f"\n{bold}>>> ARTIFACTS GENERATED <<<{reset}")
    print(f" • Structured JSON Report : {file_paths['json']}")
    print(f" • Venue Inventory CSV   : {file_paths['csv']}")
    print("=" * 78 + "\n")


def main() -> None:
    args = parse_arguments()

    if not args.pincode and not args.area:
        print("Error: You must provide at least a --pincode (e.g. 500034) or an --area (e.g. 'Banjara Hills').", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key or GOOGLE_API_KEY
    use_mock = args.mock or not bool(api_key)

    if not api_key and not args.mock:
        print("[INFO] No GOOGLE_API_KEY detected. Running in mock demonstration mode.", file=sys.stderr)
        print("[INFO] (Set GOOGLE_API_KEY or supply --api-key to run against live Google Places API).", file=sys.stderr)

    # 1. Initialize Collector & Geocode Target
    collector = PlacesCollector(api_key=api_key, use_mock=use_mock)
    lat, lng, resolved_label = collector.geocode_target(pincode=args.pincode, area=args.area)

    # Infer effective area name if not explicitly provided
    effective_area = args.area
    if not effective_area:
        if "(" in resolved_label:
            effective_area = resolved_label.split("(")[0].strip()
        else:
            effective_area = resolved_label.split(",")[0].strip()

    # 2. Collect Places (checks local disk cache first)
    raw_data = collector.collect_all_categories(
        lat=lat,
        lng=lng,
        radius=args.radius,
        pincode=args.pincode,
        area=args.area or effective_area,
        refresh_cache=args.refresh
    )
    venues = raw_data.get("venues", [])

    # 3. Analyze Data
    proxy_store = RealEstateProxyStore(custom_proxy_path=args.custom_proxies)
    analyzer = AffluenceAnalyzer(proxy_store=proxy_store)

    analysis_results = analyzer.analyze(
        venues=venues,
        pincode=args.pincode,
        area=args.area or effective_area,
        radius_meters=args.radius
    )
    # Inject spatial coordinates into target info
    analysis_results["target"]["latitude"] = lat
    analysis_results["target"]["longitude"] = lng
    analysis_results["target"]["resolved_label"] = resolved_label

    # 4. Export Artifacts
    clean_area = (args.area or effective_area or "Area").replace(" ", "_").replace("/", "_")
    pincode_tag = args.pincode or "Hyderabad"
    file_prefix = f"{pincode_tag}_{clean_area}"

    file_paths = export_reports(
        analysis_results=analysis_results,
        venues=venues,
        output_dir=args.output_dir,
        file_prefix=file_prefix
    )

    # 5. Render Terminal Summary
    render_terminal_summary(
        analysis=analysis_results,
        file_paths=file_paths,
        is_mock=raw_data.get("is_mock", use_mock),
        from_cache=raw_data.get("from_cache", False)
    )


if __name__ == "__main__":
    main()

