
"""Earliest-Deadline-First dispatch policy using a min-heap."""
import heapq
from typing import Dict, List
from simulator.models import Parcel, SimulationContext

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Select feasible parcels in earliest-deadline order."""
    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    capacity = context["capacity"]
    max_distance = context["max_trip_distance_km"]
    cutoff = context["return_cutoff"]

    # Build a min-heap ordered by deadline, then parcel ID.
    waiting = []
    for pid, record in parcel.items():
        if record["vehicle_assigned"] is None:
            heapq.heappush(
                waiting,
                (record["delivery_window_end"], pid),
            )

    route: List[str] = []
    load = 0.0
    travelled = 0.0
    location = HUB
    delivery_time = departure

    while waiting:
        selected = None

        # Find the earliest-deadline parcel feasible at this route position.
        while waiting:
            _, pid = heapq.heappop(waiting)
            record = parcel[pid]

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
            if not (
                record["delivery_window_start"]
                <= arrival
                <= record["delivery_window_end"]
            ):
                continue

            selected = (
                pid,
                destination,
                arrival,
                new_distance,
                record["size"],
            )
            break

        if selected is None:
            break

        pid, destination, arrival, new_distance, size = selected
        route.append(pid)
        load += size
        travelled = new_distance
        location = destination
        delivery_time = arrival

    return route
