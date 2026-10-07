# UrbanGravity 🏙️🧲

<p align="center">
  <img src="assets/urbangravity_logo.png" alt="UrbanGravity Logo" width="380" />
</p>

**UrbanGravity** is a geospatial economic intelligence and real estate analytics platform designed specifically for Indian metropolitan micro-markets, calibrated initially for **Hyderabad, Telangana**.

The engine evaluates target PIN codes (e.g., `500034`, `500081`, `500072`, `501401`) or neighborhood names (e.g., *Banjara Hills*, *Madhapur*, *Kukatpally*, *Medchal*), interrogates the **Google Places API (New)** across commercial anchor categories, calculates quantitative gravity indices (Premium Density Index, Footfall Volume, Affluence Score), and automatically classifies the micro-market into one of four distinct demographic tiers.

---

## 1. Demographic & Economic Tier Taxonomy

Hyderabad micro-markets exhibit sharp socio-economic stratification over short spatial distances. UrbanGravity automatically categorizes areas into:

| Tier | Classification Title | Representative Micro-Markets | Key Archetypes & Signatures |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Ultra-Affluent / High Discretionary Spending** | Banjara Hills (500034), Jubilee Hills (500033), Film Nagar (500096) | Clustered marquee luxury automotive flagships (Porsche, BMW, Mercedes-Benz, Audi, Lexus, Jaguar Land Rover), fine dining, gourmet pantries (Q-Mart, Nature's Basket), high commercial/residential rentals (₹75–₹110/sq.ft). |
| **Tier 2** | **High-Growth IT / Corporate Hub** | Madhapur (500081), Gachibowli (500032), Hitec City, Financial District (500075) | High concentration of craft microbreweries (Broadway, Zero40, Ironhill), specialty third-wave cafes (Blue Tokai, Third Wave Coffee, Roast CCX), high consumer review volume (100k+ reviews), corporate tech spending (₹50–₹70/sq.ft). |
| **Tier 3** | **Dense Middle-Income Residential / Retail Corridor** | Kukatpally (500072), Dilsukhnagar (500060), Ameerpet (500016), KPHB | Dense commercial footprint dominated by educational coaching institutes (Sri Chaitanya, Narayana), PG student hostels, traditional Andhra mess/tiffin centers (Chutneys, Babai Hotel), mass retail (DMart, Vijetha), ₹22–₹35/sq.ft. |
| **Tier 4** | **Emerging / Price-Sensitive District** | Medchal (501401), Patancheru (502319), Ghatkesar (501301) | Periphery micro-market with lower commercial density, localized unorganized retail, and value-focused spending (₹12–₹20/sq.ft). |

---

## 2. Quantitative Scoring Methodology

### 2.1 Premium Density Index (PDI)
Measures the proportion of high-discretionary commercial anchors relative to the total commercial venues:
$$\text{PDI} = \frac{N_{\text{Luxury Automotive}} + N_{\text{Breweries \& Specialty Cafes}} + N_{\text{Gourmet Retail}}}{\max(1, N_{\text{Total Scraped Venues}})}$$

### 2.2 Mass / Value Density Index (MDI)
Measures the proportion of budget dining, student hostels, and coaching institutes:
$$\text{MDI} = \frac{N_{\text{Budget Tiffins \& Mess}} + N_{\text{Hostels \& Coaching}}}{\max(1, N_{\text{Total Scraped Venues}})}$$

### 2.3 Review Volume Score (RVS)
Measures commercial footfall vibrancy and active consumer activity on a normalized logarithmic scale ($0 \text{ to } 100$):
$$\text{RVS} = \min\left(100.0, \frac{\log_{10}(1 + \sum \text{userRatingCount})}{5.0} \times 100.0\right)$$
*(A total of 100,000+ consumer reviews scales to 100.0).*

### 2.4 Composite Affluence Score ($0 \text{ to } 100$)
A weighted composite incorporating:
1. **Luxury Automotive Anchor Presence (Max 25 pts)**: Heavy weighting for marquee luxury automotive presence (exclusive to elite Indian micro-markets).
2. **Premium Density Component (Max 30 pts)**: Ratio of lifestyle and discretionary anchors.
3. **Lifestyle F&B & Wellness Density (Max 15 pts)**: Density of microbreweries, third-wave coffee, and boutique fitness.
4. **Real Estate Benchmark Rental (Max 20 pts)**: Based on Hyderabad micro-market rental benchmark (₹/sq.ft/month).
5. **Footfall & Vibrancy Score (Max 10 pts)**: Log-normalized review volume.
6. **Mass Discount Penalty (Up to -15 pts)**: Discount applied for high concentrations of budget student hostels, coaching centres, and mess stalls.

---

## 3. Modular Architecture

```
UrbanGravity/
├── config.py             # Places API (New) endpoints, query buckets, weights, Hyderabad benchmarks
├── collectors/
│   ├── __init__.py       # Collectors package
│   └── places.py         # Geocoding + Places API (New) Text Search client, deduplication & mock generator
├── analyzer.py           # Quantitative formulas (PDI, RVS, Affluence Score), Tier decision tree, Proxy store
├── main.py               # CLI entrypoint (argparse), report exporter, rich executive terminal summary
├── requirements.txt      # Dependencies (googlemaps, pandas, requests, python-dotenv)
├── README.md             # Documentation and usage guide
├── data/                 # Sample reference rental & dining cost proxies
└── outputs/              # Generated JSON and CSV reports
    ├── 500034_Banjara_Hills_report.json
    └── 500034_Banjara_Hills_venues.csv
```

---

## 4. Installation & Setup

### 4.1 Prerequisites
- Python 3.9+ (tested up to Python 3.14)

### 4.2 Clone & Install Dependencies
```bash
git clone <repo-url>
cd UrbanGravity

# Create and activate virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 5. Setting up Google Places API (New)

### 5.1 Enable APIs in Google Cloud Console
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a Google Cloud Project.
3. In the **APIs & Services > Library**, enable:
   - **Places API (New)** (`places.googleapis.com`)
   - **Geocoding API** (`maps.googleapis.com`)
4. Create an API Key in **APIs & Services > Credentials**.

### 5.2 Set API Key in Environment
You can configure the API Key via:

**Option A: Environment Variable (Recommended)**
```bash
export GOOGLE_API_KEY="AIzaSyYourGoogleApiKeyHere"
```

**Option B: `.env` File**
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=AIzaSyYourGoogleApiKeyHere
```

**Option C: CLI Argument**
Pass it directly via the `--api-key` parameter:
```bash
python3 main.py --pincode 500034 --area "Banjara Hills" --api-key "AIzaSyYourGoogleApiKeyHere"
```

### 5.3 Cost Protection: Set Quota Limits (Avoid Surprise Charges)
To prevent unexpected bill shocks from automated loops or testing, set safety caps in [Google Cloud Maps Quotas](https://console.cloud.google.com/google/maps-apis/quotas):

Under **Places API (New)**, edit these two limits:
1. **`SearchTextRequest per day`**: Reduce from `75,000` to **`350`** (or `500`).
   - *Rationale*: 1 neighborhood run executes ~32 text searches. 350 allows ~10 full runs/day, capping maximum worst-case daily exposure to ~$7 USD.
2. **`SearchTextRequest per minute`**: Reduce from `600` to **`60`**.
   - *Rationale*: Instantly throttles runaway CLI loops before they drain credits.

---

## 6. CLI Usage & Examples

### 6.1 Command-Line Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--pincode` | `str` | `None` | Target 6-digit Indian PIN Code (e.g. `500034`, `500081`, `500072`) |
| `--area` | `str` | `None` | Target Neighborhood name (e.g. `"Banjara Hills"`, `"Madhapur"`) |
| `--radius` | `int` | `4000` | Search radius in meters (default: 4,000m / 4km) |
| `--api-key` | `str` | `""` | Google Cloud API key (falls back to `GOOGLE_API_KEY` env var) |
| `--mock` | `flag` | `False` | Run in offline benchmark mode with realistic Hyderabad datasets |
| `--output-dir` | `str` | `"outputs"` | Directory to store CSV and JSON reports |
| `--custom-proxies` | `str` | `None` | Path to custom scraped JSON or CSV file for real estate rental/cost proxies |

### 6.2 Running Hyderabad Archetype Benchmark Evaluations

When no API key is configured or `--mock` is passed, the tool uses an authentic pre-seeded offline dataset of Hyderabad commercial anchors:

#### 1. Tier 1: Ultra-Affluent (Banjara Hills / Jubilee Hills)
```bash
python3 main.py --pincode 500034 --area "Banjara Hills"
```
*Evaluates to Tier 1 with 5 luxury auto showrooms (Porsche, BMW, Mercedes, Audi, Jaguar Land Rover), Roastery Coffee House, Q-Mart, and 98+ Affluence Score.*

#### 2. Tier 2: High-Growth IT Hub (Madhapur / Hitec City)
```bash
python3 main.py --pincode 500081 --area "Madhapur"
```
*Evaluates to Tier 2 with 7 microbreweries & specialty cafes (Broadway, Zero40, Ironhill, Blue Tokai, Third Wave Coffee), 120k+ review footfall, and 66+ Affluence Score.*

#### 3. Tier 3: Dense Middle-Income Residential / Retail (Kukatpally / KPHB)
```bash
python3 main.py --pincode 500072 --area "Kukatpally"
```
*Evaluates to Tier 3 with high Mass Density Index (50%) dominated by coaching centers (Sri Chaitanya, Narayana), PG hostels, and authentic tiffin centers (Babai Hotel, Chutneys).*

#### 4. Tier 4: Emerging / Price-Sensitive (Medchal)
```bash
python3 main.py --pincode 501401 --area "Medchal"
```
*Evaluates to Tier 4 with sparse commercial density, unorganized kirana stores, and low rental rates (₹16/sq.ft).*

---

## 7. Real Estate Cost-of-Living Ingestion (Stub / Custom Scrapers)

You can pass external scraped datasets (e.g., scraped from MagicBricks, 99acres, Housing.com, or Zomato) using `--custom-proxies`:

### Custom JSON Format
```json
{
  "500034": {
    "area_name": "Banjara Hills Prime",
    "avg_rent_sqft_inr": 85.0,
    "avg_cost_for_two_inr": 3000.0,
    "benchmark_tier": "Tier 1",
    "archetype": "Super-Prime Luxury Residential Enclave"
  }
}
```

### Custom CSV Format
```csv
pincode,area_name,avg_rent_sqft_inr,avg_cost_for_two_inr,benchmark_tier,archetype
500034,Banjara Hills,85.0,3000.0,Tier 1,Super-Prime Luxury Enclave
500081,Madhapur,60.0,2000.0,Tier 2,IT & Corporate Corridor
```

Run CLI with:
```bash
python3 main.py --pincode 500034 --area "Banjara Hills" --custom-proxies custom_rentals.json
```

---

## 8. Output Artifacts

Every execution automatically generates two files in `outputs/`:

1. **Structured JSON Report (`<pincode>_<area>_report.json`)**:
   Contains spatial centroid coordinates, demographic tier classification, composite scores (`affluence_score`, `pdi`, `mdi`, `rvs`), category breakdowns, and real estate benchmarks.
2. **Venue Inventory CSV (`<pincode>_<area>_venues.csv`)**:
   Tabular dataset listing all individual commercial venues found:
   - `place_id`: Unique Google Place ID
   - `name`: Business / Venue name
   - `primary_type`: Google Place primary type
   - `rating`: Google user rating (1.0 - 5.0)
   - `user_ratings_count`: Total user review count
   - `formatted_address`: Full street address
   - `latitude` / `longitude`: Geolocation
   - `categories`: Matched category bucket(s)
   - `matched_queries`: Specific query keywords matched

