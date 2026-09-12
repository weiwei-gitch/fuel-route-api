# Fuel Route Optimization API

Django REST API for planning a USA driving route and selecting cost-effective fuel stops from the supplied fuel-price dataset.

## Stack
- Django 6.1.1
- Django REST Framework
- OpenRouteService / HeiGIT for geocoding and driving directions
- U.S. Census Gazetteer 2026 for offline station city/state coordinates
- pandas, Shapely, pyproj

Django 6.1.1 is the current official stable release as of this project.

## Setup
```bash
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
```
Put your OpenRouteService API key in `.env` as `ORS_API_KEY`. The API uses the current HeiGIT endpoint, not the deprecated `api.openrouteservice.org` endpoint.

## Prepare fuel data
The supplied CSV contains station city/state and prices but no latitude/longitude. Run:
```bash
python scripts/enrich_fuel_prices.py
```
This performs a one-time offline data preparation step using the 2026 U.S. Census Places Gazetteer. It filters non-US records, deduplicates by station ID using the lowest listed retail price, and adds representative city/place coordinates. The Census files provide representative latitude/longitude coordinates.

## Run
```bash
python manage.py runserver
```

Health check:
`GET http://127.0.0.1:8000/api/health/`

Route endpoint:
`POST http://127.0.0.1:8000/api/route/`

Body:
```json
{"start":"New York, NY","finish":"Chicago, IL"}
```

The endpoint performs two geocoding calls and one directions call. Station matching and fuel optimization are local operations.

## Optimization assumptions
- Vehicle range: 500 miles
- Fuel economy: 10 MPG
- Implied tank capacity: 50 gallons
- Vehicle starts with a full tank
- Starting fuel is considered already paid for and excluded from trip cost
- Stations are matched within a 15-mile corridor around the route
- Station coordinates are representative city/place coordinates, so they are an approximation
- If no feasible station sequence exists, the API returns an error rather than an invalid plan

## Response
The response contains total road distance, total gallons consumed, total fuel cost, selected fuel stops, and the route as GeoJSON so a client can render the map.

## Tests
```bash
python manage.py test
```
