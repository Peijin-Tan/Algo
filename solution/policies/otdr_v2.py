
"""Dispatch policy using on-time feasibility and one-step lookahead."""
from typing import Dict, List
from simulator.models import Parcel, SimulationContext

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    capacity = context["capacity"]
    max_distance = context["max_trip_distance_km"]
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
    delivery_time = departure

    while waiting:
        candidates = []

        for pid, record in waiting.items():
            if load + record["size"] > capacity:
                continue

            destination = record["delivery_location_id"]
            leg = distances[location][destination]
            arrival = delivery_time + leg
            new_distance = travelled + leg
            round_trip = new_distance + distances[destination][HUB]

            if round_trip > max_distance:
                continue
            if departure + round_trip > cutoff:
                continue

            start = record["delivery_window_start"]
            end = record["delivery_window_end"]

            # Only consider parcels that can arrive within their window.
            if not (start <= arrival <= end):
                continue

            # Estimate how many other waiting parcels remain feasible
            # immediately after delivering this candidate.
            remaining_capacity = capacity - load - record["size"]
            next_options = 0

            for other_id, other in waiting.items():
                if other_id == pid:
                    continue
                if other["size"] > remaining_capacity:
                    continue

                other_destination = other["delivery_location_id"]
                next_leg = distances[destination][other_destination]
                other_arrival = arrival + next_leg
                next_distance = new_distance + next_leg
                next_round_trip = (
                    next_distance + distances[other_destination][HUB]
                )

                if next_round_trip > max_distance:
                    continue
                if departure + next_round_trip > cutoff:
                    continue

                if (
                    other["delivery_window_start"]
                    <= other_arrival
                    <= other["delivery_window_end"]
                ):
                    next_options += 1

            # Prefer more future options, then shorter travel,
            # then earlier deadlines and stable parcel IDs.
            candidates.append((
                -next_options,
                leg,
                end,
                pid,
                arrival,
                new_distance,
                destination,
            ))

        if not candidates:
            break

        candidates.sort()
        (
            _,
            _,
            _,
            pid,
            arrival,
            new_distance,
            destination,
        ) = candidates[0]

        record = waiting.pop(pid)
        route.append(pid)
        load += record["size"]
        travelled = new_distance
        location = destination
        delivery_time = arrival

    return route
