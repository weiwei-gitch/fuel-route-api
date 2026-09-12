from pathlib import Path

import pandas as pd
from django.conf import settings


US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT "
    "VA WA WV WI WY DC".split()
)


def normalize(value):
    return " ".join(
        str(value).strip().upper().replace(".", "").split()
    )


def load_fuel_data(path=None):
    path = Path(path or settings.ENRICHED_FUEL_CSV_PATH)

    if not path.exists():
        raise FileNotFoundError(
            f"Enriched fuel dataset not found at {path}. "
            "Run: python scripts/enrich_fuel_prices.py"
        )

    df = pd.read_csv(path)

    # The enriched CSV uses the original column names from the
    # assessment dataset. Normalize them to the names used internally.
    df = df.rename(
        columns={
            "OPIS Truckstop ID": "station_id",
            "Truckstop Name": "truckstop_name",
            "Address": "address",
            "City": "city",
            "State": "state",
            "Rack ID": "rack_id",
            "Retail Price": "retail_price",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )

    required = {
        "station_id",
        "truckstop_name",
        "address",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Enriched dataset missing columns: {sorted(missing)}"
        )

    # Keep only valid US stations with usable coordinates and prices.
    df["state"] = df["state"].astype(str).str.strip().str.upper()

    df = df[df["state"].isin(US_STATES)].copy()

    df["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )

    df["retail_price"] = pd.to_numeric(
        df["retail_price"], errors="coerce"
    )

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "retail_price",
        ]
    )

    # The enrichment step already deduplicates stations, but this
    # also protects the API if duplicate station IDs exist.
    df = (
        df.sort_values("retail_price")
        .drop_duplicates(
            subset=["station_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    return df