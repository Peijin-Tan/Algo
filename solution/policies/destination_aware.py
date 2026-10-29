
"""Dispatch policy that groups on-time parcels by destination."""
from typing import Dict, List
from simulator.models import Parcel, SimulationContext

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Prioritise destination groups to deliver more parcels on time."""
    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    max_distance = context["max_trip_distance_km"]
    capacity = context["capacity"]
    cutoff = context["return_cutoff"]

    waiting = {
        pid: record
        for pid, record in parcel.items()
        if record["vehicle_assigned"] is None
    }

    route: List[str] = []
    load = 0.0
    travelled = 0.0
    location = HUB
    current_time = departure

    while waiting:
        # Group currently waiting parcels by delivery destination.
        groups = {}
        for pid, record in waiting.items():
            destination = record["delivery_location_id"]
            groups.setdefault(destination, []).append((pid, record))

        candidates = []

        for destination, parcels_at_location in groups.items():
            leg = distances[location][destination]
            arrival = current_time + leg
            new_distance = travelled + leg
            round_trip = new_distance + distances[destination][HUB]

            # Enforce the trip's hard constraints.
            if load > capacity:
                continue
            if departure + round_trip > cutoff:
                continue
            if round_trip > max_distance:
                continue

            # Only consider parcels that can be delivered on time.
            eligible = [
                (pid, record)
                for pid, record in parcels_at_location
                if record["delivery_window_start"]
                <= arrival
                <= record["delivery_window_end"]
            ]

            # Prefer fitting as many parcels as possible.
            # Smaller parcels are considered first to maximise parcel count.
            eligible.sort(
                key=lambda item: (
                    item[1]["size"],
                    item[1]["delivery_window_end"],
                    item[0],
                )
            )

            chosen = []
            remaining_capacity = capacity - load

            for pid, record in eligible:
                if record["size"] <= remaining_capacity + 1e-9:
                    chosen.append((pid, record))
                    remaining_capacity -= record["size"]

            if not chosen:
                continue

            earliest_deadline = min(
                record["delivery_window_end"]
                for _, record in chosen
            )

            # Prefer more on-time parcels, then shorter travel,
            # then earlier deadlines.
            candidates.append(
                (
                    -len(chosen),
                    leg,
                    earliest_deadline,
                    destination,
                    arrival,
                    new_distance,
                    chosen,
                )
            )

        if not candidates:
            break

        candidates.sort(key=lambda candidate: candidate[:4])

        (
            _,
            leg,
            _,
            destination,
            arrival,
            new_distance,
            chosen,
        ) = candidates[0]

        for pid, record in chosen:
            route.append(pid)
            load += record["size"]
            waiting.pop(pid)

        travelled = new_distance
        location = destination
        current_time = arrival

    return route
