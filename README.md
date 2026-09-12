# Fuel Route API

A Django REST API that calculates a driving route between two locations in the USA and recommends cost-effective fuel stops along the route.

The API uses OpenRouteService for routing and a provided fuel-price dataset to determine suitable refueling stops for a vehicle with a maximum range of 500 miles.

## Features

- Accepts start and finish locations in the USA
- Calculates a driving route using OpenRouteService
- Returns route information as GeoJSON
- Finds fuel stations near the calculated route
- Considers a maximum vehicle range of 500 miles
- Assumes fuel efficiency of 10 MPG
- Selects cost-effective fuel stops based on available fuel prices
- Calculates fuel consumed and total fuel cost
- Validates API input
- Includes automated tests

## Tech Stack

- Python
- Django
- Django REST Framework
- Pandas
- OpenRouteService API
- CSV fuel-price dataset

## API Endpoint

### Calculate Route

```http
POST /api/route/
