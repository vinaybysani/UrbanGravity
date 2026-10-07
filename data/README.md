# Data Directory: Real Estate & Cost-of-Living Proxies

This directory contains reference proxy datasets for Hyderabad micro-markets.

## Schema

### JSON Schema (`sample_hyderabad_rentals.json`)
```json
{
  "<PINCODE>": {
    "area_name": "Neighborhood Name",
    "avg_rent_sqft_inr": 80.0,
    "avg_cost_for_two_inr": 2500.0,
    "benchmark_tier": "Tier 1",
    "archetype": "Description of Micro-Market Archetype"
  }
}
```

### CSV Schema (`sample_hyderabad_rentals.csv`)
Columns:
- `pincode`: 6-digit Indian Postal PIN Code
- `area_name`: Micro-market or neighborhood name
- `avg_rent_sqft_inr`: Average monthly rent per sq. ft (commercial/residential composite in INR)
- `avg_cost_for_two_inr`: Average dining cost for two people in INR
- `benchmark_tier`: Target demographic tier classification (`Tier 1`, `Tier 2`, `Tier 3`, `Tier 4`)
- `archetype`: Qualitative socio-economic description

## Usage with CLI
Pass either JSON or CSV files into the CLI using the `--custom-proxies` flag:
```bash
python3 main.py --pincode 500034 --area "Banjara Hills" --custom-proxies data/sample_hyderabad_rentals.json
python3 main.py --pincode 500081 --area "Madhapur" --custom-proxies data/sample_hyderabad_rentals.csv
```

