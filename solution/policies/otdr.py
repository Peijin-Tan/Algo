
"""Dispatch policy prioritising feasible on-time deliveries."""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext

HUB = "HUB"


def dispatch(
    parcel: Dict[str, Parcel],
    context: SimulationContext,
) -> List[str]:
    """Build a feasible route that prioritises on-time deliveries."""

    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    max_distance = context["max_trip_distance_km"]
    capacity = context["capacity"]
    cutoff = context["return_cutoff"]

    waiting = {
        parcel_id: record
        for parcel_id, record in parcel.items()
        if record["vehicle_assigned"] is None
    }

    route: List[str] = []
    load = 0.0
    travelled = 0.0
    location = HUB
    current_delivery_time = departure

    while waiting:
        candidates = []

        for parcel_id, record in waiting.items():
            if load + record["size"] > capacity:
                continue

            destination = record["delivery_location_id"]
            leg = distances[location][destination]
            arrival = current_delivery_time + leg

            # Check the complete route, including the return to the hub.
            new_distance = travelled + leg
            round_trip = new_distance + distances[destination][HUB]

            if round_trip > max_distance:
                continue

            if departure + round_trip > cutoff:
                continue

            start = record["delivery_window_start"]
            end = record["delivery_window_end"]

            # Prefer parcels that can be delivered within their windows.
            on_time = start <= arrival <= end

            # Prefer on-time candidates, then shorter legs and earlier deadlines.
            candidates.append(
                (
                    0 if on_time else 1,
                    leg,
                    end,
                    parcel_id,
                    arrival,
                    new_distance,
                )
            )

        if not candidates:
            break

        candidates.sort()
        (
            priority,
            leg,
            deadline,
            parcel_id,
            arrival,
            new_distance,
        ) = candidates[0]

        # If no candidate can be delivered on time, don't add late parcels.
        if priority != 0:
            break

        record = waiting.pop(parcel_id)
        route.append(parcel_id)
        load += record["size"]
        travelled = new_distance
        location = record["delivery_location_id"]
        current_delivery_time = arrival

    return route
