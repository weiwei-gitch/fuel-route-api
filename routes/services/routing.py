import truststore

# Use Windows' certificate store for HTTPS verification.
truststore.inject_into_ssl()

import requests
from django.conf import settings


class RoutingError(Exception):
    pass


def _headers():
    if not settings.ORS_API_KEY:
        raise RoutingError(
            "ORS_API_KEY is not configured. Add it to .env."
        )

    return {
        "Authorization": settings.ORS_API_KEY,
    }


def geocode(place):
    """
    Convert a US place name into latitude/longitude.
    """

    url = "https://api.heigit.org/pelias/v1/search"

    params = {
        "text": place,
        "boundary.country": "USA",
        "size": 1,
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=_headers(),
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as e:
        raise RoutingError(
            f"Geocoding failed for {place}: {e}"
        )

    features = data.get("features", [])

    if not features:
        raise RoutingError(
            f"Could not find a US location for: {place}"
        )

    feature = features[0]

    coordinates = feature.get("geometry", {}).get("coordinates")

    if not coordinates or len(coordinates) < 2:
        raise RoutingError(
            f"Geocoding returned invalid coordinates for: {place}"
        )

    properties = feature.get("properties", {})

    return {
        "label": properties.get("label", place),
        "longitude": float(coordinates[0]),
        "latitude": float(coordinates[1]),
    }


def get_route(start, finish):
    """
    Get a driving route between two locations.

    ORS expects coordinates in:
        longitude,latitude

    The GET directions endpoint returns GeoJSON.
    """

    url = (
        f"{settings.ORS_BASE_URL}"
        "/v2/directions/driving-car"
    )

    params = {
        "start": (
            f"{start['longitude']},"
            f"{start['latitude']}"
        ),
        "end": (
            f"{finish['longitude']},"
            f"{finish['latitude']}"
        ),
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=_headers(),
            timeout=45,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as e:
        raise RoutingError(
            f"Routing failed: {e}"
        )

    features = data.get("features", [])

    if not features:
        raise RoutingError(
            "Routing service returned no route."
        )

    feature = features[0]

    properties = feature.get("properties", {})
    summary = properties.get("summary", {})

    distance_meters = float(
        summary.get("distance", 0)
    )

    duration_seconds = float(
        summary.get("duration", 0)
    )

    return {
        "geojson": feature,
        "distance_miles": distance_meters / 1609.344,
        "duration_seconds": duration_seconds,
    }