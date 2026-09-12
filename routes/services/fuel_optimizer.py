from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform
from django.conf import settings


_transformer = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:5070",
    always_xy=True,
)


def _project_geometry(route_feature):
    coords = route_feature["geometry"]["coordinates"]
    line = LineString(coords)
    projected_line = transform(_transformer.transform, line)
    return projected_line


def candidates_on_route(route_feature, stations, buffer_miles=None):
    """
    Find fuel stations close to the route and calculate their
    approximate position along the route in miles.
    """

    if buffer_miles is None:
        buffer_miles = settings.ROUTE_BUFFER_MILES

    projected_line = _project_geometry(route_feature)

    corridor = projected_line.buffer(
        buffer_miles * 1609.344
    )

    total_route_miles = projected_line.length / 1609.344

    result = []

    for row in stations.itertuples(index=False):
        point = Point(
            float(row.longitude),
            float(row.latitude),
        )

        projected_point = transform(
            _transformer.transform,
            point,
        )

        if not corridor.covers(projected_point):
            continue

        route_mile = (
            projected_line.project(projected_point)
            / 1609.344
        )

        if route_mile < 0 or route_mile > total_route_miles:
            continue

        result.append(
            {
                "station_id": int(row.station_id),
                "name": str(row.truckstop_name),
                "city": str(row.city),
                "state": str(row.state),
                "price": float(row.retail_price),
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "route_mile": float(route_mile),
            }
        )

    return sorted(
        result,
        key=lambda x: x["route_mile"],
    )


def optimize_stops(total_miles, candidates, mpg=10, max_range=500):
    """
    Find cost-effective fuel stops.

    Assumptions:
    - Vehicle starts with a full tank.
    - Fuel economy = 10 MPG.
    - Maximum range = 500 miles.
    - Therefore tank capacity = 50 gallons.
    - Initial fuel cost is not included.
    - Fuel can be purchased in arbitrary quantities.

    Strategy:
    At each station:
    - If a cheaper reachable station exists, buy only enough
      fuel to reach that cheaper station.
    - Otherwise, fill the tank and continue to the farthest
      feasible station.
    """

    if total_miles <= max_range:
        return [], total_miles / mpg, 0.0

    if not candidates:
        raise ValueError(
            "No fuel stations were found along the route corridor."
        )

    tank_capacity = max_range / mpg

    # Only stations between start and finish.
    stations = [
        station
        for station in candidates
        if 0 < station["route_mile"] < total_miles
    ]

    if not stations:
        raise ValueError(
            "No fuel stations are available before the destination."
        )

    # Remove stations that are essentially at the same position.
    compact = []

    for station in stations:
        if (
            not compact
            or station["route_mile"]
            - compact[-1]["route_mile"]
            > 0.1
        ):
            compact.append(station)
        elif station["price"] < compact[-1]["price"]:
            compact[-1] = station

    stations = compact

    # ---------------------------------------------------------
    # Determine which stations can eventually reach the finish.
    # ---------------------------------------------------------

    safe = [False] * len(stations)

    for i in range(len(stations) - 1, -1, -1):
        current_mile = stations[i]["route_mile"]

        # Can this station directly reach the destination?
        if total_miles - current_mile <= max_range + 1e-9:
            safe[i] = True
            continue

        # Otherwise, can it reach another safe station?
        for j in range(i + 1, len(stations)):
            distance = (
                stations[j]["route_mile"]
                - current_mile
            )

            if distance > max_range + 1e-9:
                break

            if safe[j]:
                safe[i] = True
                break

    # ---------------------------------------------------------
    # Choose the first station.
    # Starting tank is already full.
    # ---------------------------------------------------------

    first_options = []

    for i, station in enumerate(stations):
        if station["route_mile"] > max_range + 1e-9:
            break

        if safe[i]:
            first_options.append(i)

    if not first_options:
        raise ValueError(
            "No feasible fuel-stop sequence exists within "
            f"the {max_range}-mile vehicle range."
        )

    # From the starting point, choose the cheapest feasible
    # station that can be reached with the initial full tank.
    current_index = min(
        first_options,
        key=lambda i: stations[i]["price"],
    )

    fuel = tank_capacity
    total_cost = 0.0
    stops = []

    # Travel from the start to the first station.
    first_distance = stations[current_index]["route_mile"]
    fuel -= first_distance / mpg

    # ---------------------------------------------------------
    # Main optimization loop.
    # ---------------------------------------------------------

    while True:
        current = stations[current_index]
        current_mile = current["route_mile"]

        distance_to_finish = total_miles - current_mile

        # We can reach the destination with fuel already available.
        if distance_to_finish <= fuel * mpg + 1e-9:
            break

        # Find reachable safe stations.
        reachable = []

        for j in range(current_index + 1, len(stations)):
            distance = (
                stations[j]["route_mile"]
                - current_mile
            )

            if distance > max_range + 1e-9:
                break

            if safe[j]:
                reachable.append((j, distance))

        # -----------------------------------------------------
        # Find the first cheaper station.
        # -----------------------------------------------------

        cheaper = None

        for j, distance in reachable:
            if stations[j]["price"] < current["price"] - 1e-9:
                cheaper = (j, distance)
                break

        previous_mile = (
            stops[-1]["route_mile"]
            if stops
            else 0.0
        )

        # -----------------------------------------------------
        # Case 1: cheaper station exists.
        # Buy only enough to reach it.
        # -----------------------------------------------------

        if cheaper is not None:
            target_index, target_distance = cheaper

            required_fuel = target_distance / mpg

            gallons_to_buy = max(
                0.0,
                required_fuel - fuel,
            )

            if fuel + gallons_to_buy > tank_capacity + 1e-9:
                raise ValueError(
                    "Unable to reach the next cheaper station."
                )

            fuel += gallons_to_buy

            cost = gallons_to_buy * current["price"]
            total_cost += cost

            if gallons_to_buy > 1e-9:
                stops.append(
                    {
                        "station_id": current["station_id"],
                        "name": current["name"],
                        "city": current["city"],
                        "state": current["state"],
                        "price_per_gallon": round(
                            current["price"],
                            4,
                        ),
                        "latitude": current["latitude"],
                        "longitude": current["longitude"],
                        "route_mile": round(
                            current_mile,
                            2,
                        ),
                        "miles_from_previous_stop": round(
                            current_mile - previous_mile,
                            2,
                        ),
                        "gallons_purchased": round(
                            gallons_to_buy,
                            3,
                        ),
                        "fuel_cost": round(
                            cost,
                            2,
                        ),
                    }
                )

            fuel -= target_distance / mpg
            current_index = target_index

        # -----------------------------------------------------
        # Case 2: no cheaper station exists.
        # Fill the tank and move to the farthest feasible station.
        # -----------------------------------------------------

        else:
            # Destination is reachable after refuelling here.
            if distance_to_finish <= max_range + 1e-9:
                required_fuel = distance_to_finish / mpg

                gallons_to_buy = max(
                    0.0,
                    required_fuel - fuel,
                )

                gallons_to_buy = min(
                    gallons_to_buy,
                    tank_capacity - fuel,
                )

                fuel += gallons_to_buy

                cost = gallons_to_buy * current["price"]
                total_cost += cost

                if gallons_to_buy > 1e-9:
                    stops.append(
                        {
                            "station_id": current["station_id"],
                            "name": current["name"],
                            "city": current["city"],
                            "state": current["state"],
                            "price_per_gallon": round(
                                current["price"],
                                4,
                            ),
                            "latitude": current["latitude"],
                            "longitude": current["longitude"],
                            "route_mile": round(
                                current_mile,
                                2,
                            ),
                            "miles_from_previous_stop": round(
                                current_mile - previous_mile,
                                2,
                            ),
                            "gallons_purchased": round(
                                gallons_to_buy,
                                3,
                            ),
                            "fuel_cost": round(
                                cost,
                                2,
                            ),
                        }
                    )

                break

            # We need another station.
            if not reachable:
                raise ValueError(
                    "No reachable fuel station within "
                    f"{max_range} miles from route mile "
                    f"{current_mile:.1f}."
                )

            # Fill the tank.
            gallons_to_buy = tank_capacity - fuel

            fuel += gallons_to_buy

            cost = gallons_to_buy * current["price"]
            total_cost += cost

            if gallons_to_buy > 1e-9:
                stops.append(
                    {
                        "station_id": current["station_id"],
                        "name": current["name"],
                        "city": current["city"],
                        "state": current["state"],
                        "price_per_gallon": round(
                            current["price"],
                            4,
                        ),
                        "latitude": current["latitude"],
                        "longitude": current["longitude"],
                        "route_mile": round(
                            current_mile,
                            2,
                        ),
                        "miles_from_previous_stop": round(
                            current_mile - previous_mile,
                            2,
                        ),
                        "gallons_purchased": round(
                            gallons_to_buy,
                            3,
                        ),
                        "fuel_cost": round(
                            cost,
                            2,
                        ),
                    }
                )

            # Go to the farthest safe station we can reach.
            target_index, target_distance = reachable[-1]

            fuel -= target_distance / mpg
            current_index = target_index

    total_fuel_consumed = total_miles / mpg

    return (
        stops,
        total_fuel_consumed,
        round(total_cost, 2),
    )