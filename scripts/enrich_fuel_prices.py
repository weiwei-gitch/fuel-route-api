"""Create an enriched station CSV using the U.S. Census 2026 Places Gazetteer.

Run from project root:
    python scripts/enrich_fuel_prices.py
"""

from pathlib import Path
import re
import zipfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "fuel-prices.csv"
CENSUS_ZIP = ROOT / "data" / "2026_Gaz_place_national.zip"
OUT = ROOT / "data" / "processed" / "fuel-prices-enriched.csv"


US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
    "WA WV WI WY DC".split()
)


def norm(value):
    """Normalize text for matching."""
    return re.sub(
        r"\s+",
        " ",
        str(value).strip().upper().replace(".", "")
    )


def city_norm(value):
    """
    Normalize a city/place name.

    Handles both:
      'Dallas'
      'Dallas city, Texas'
    """
    s = norm(value)

    # Census NAME can be:
    # "Dallas city, Texas"
    # "Phoenix city, Arizona"
    if "," in s:
        s = s.split(",", 1)[0].strip()

    # Remove legal/statistical suffixes.
    s = re.sub(
        r"\s+(CITY|TOWN|VILLAGE|BOROUGH|MUNICIPALITY|CDP|COUNTY|PARISH)$",
        "",
        s,
    )

    return s


def main():
    if not RAW.exists():
        raise FileNotFoundError(f"Fuel price CSV not found: {RAW}")

    if not CENSUS_ZIP.exists():
        raise FileNotFoundError(
            f"Census ZIP not found: {CENSUS_ZIP}\n"
            "Place 2026_Gaz_place_national.zip inside the data folder."
        )

    # ---------------------------------------------------------
    # 1. Load fuel-price data
    # ---------------------------------------------------------

    df = pd.read_csv(RAW)

    # Keep only U.S. stations.
    df = df[
        df["State"]
        .astype(str)
        .str.upper()
        .isin(US_STATES)
    ].copy()

    # Make sure prices are numeric.
    df["Retail Price"] = pd.to_numeric(
        df["Retail Price"],
        errors="coerce",
    )

    df = df.dropna(subset=["Retail Price"])

    # If the same station ID occurs multiple times,
    # keep the cheapest observed price.
    df = (
        df.sort_values("Retail Price")
        .drop_duplicates("OPIS Truckstop ID", keep="first")
    )

    original_station_count = len(df)

    print(f"US deduplicated stations: {original_station_count}")

    # ---------------------------------------------------------
    # 2. Read Census Places Gazetteer from local ZIP
    # ---------------------------------------------------------

    with zipfile.ZipFile(CENSUS_ZIP, "r") as z:
        txt_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".txt")
        ]

        if not txt_files:
            raise RuntimeError(
                "No .txt file found inside the Census ZIP."
            )

        census_file = txt_files[0]

        print(f"Reading Census file: {census_file}")

        with z.open(census_file) as f:
            places = pd.read_csv(
                f,
                sep="|",
                dtype=str,
            )

    # Clean column names.
    places.columns = [
        c.strip().upper()
        for c in places.columns
    ]

    required_columns = {
        "USPS",
        "NAME",
        "INTPTLAT",
        "INTPTLONG",
    }

    missing = required_columns - set(places.columns)

    if missing:
        raise RuntimeError(
            f"Census file is missing columns: {sorted(missing)}"
        )

    # ---------------------------------------------------------
    # 3. Build city + state -> coordinates lookup
    # ---------------------------------------------------------

    places["CITY_KEY"] = places["NAME"].map(city_norm)
    places["STATE_KEY"] = places["USPS"].map(norm)

    places["latitude"] = pd.to_numeric(
        places["INTPTLAT"],
        errors="coerce",
    )

    places["longitude"] = pd.to_numeric(
        places["INTPTLONG"],
        errors="coerce",
    )

    places = places.dropna(
        subset=["latitude", "longitude"]
    )

    # One representative point per city/state.
    places = places.drop_duplicates(
        subset=["CITY_KEY", "STATE_KEY"]
    )

    lookup = (
        places
        .set_index(["CITY_KEY", "STATE_KEY"])[
            ["latitude", "longitude"]
        ]
        .to_dict("index")
    )

    # ---------------------------------------------------------
    # 4. Match fuel stations to Census city coordinates
    # ---------------------------------------------------------

    df["CITY_KEY"] = df["City"].map(city_norm)
    df["STATE_KEY"] = df["State"].map(norm)

    coords = [
        lookup.get((city, state))
        for city, state in zip(
            df["CITY_KEY"],
            df["STATE_KEY"],
        )
    ]

    df["latitude"] = [
        item["latitude"] if item else None
        for item in coords
    ]

    df["longitude"] = [
        item["longitude"] if item else None
        for item in coords
    ]

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce",
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce",
    )

    unmatched_count = int(
        df["latitude"].isna().sum()
        | df["longitude"].isna().sum()
    )

    df = df.dropna(
        subset=["latitude", "longitude"]
    )

    # ---------------------------------------------------------
    # 5. Write enriched CSV
    # ---------------------------------------------------------

    out = df[
        [
            "OPIS Truckstop ID",
            "Truckstop Name",
            "Address",
            "City",
            "State",
            "Rack ID",
            "Retail Price",
            "latitude",
            "longitude",
        ]
    ].rename(
        columns={
            "OPIS Truckstop ID": "station_id",
            "Truckstop Name": "truckstop_name",
            "Retail Price": "retail_price",
        }
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.to_csv(
        OUT,
        index=False,
    )

    print(f"Enriched stations: {len(out)}")
    print(f"Unmatched stations: {unmatched_count}")
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()