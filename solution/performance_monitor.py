"""Calculate performance metrics from one simulation run's event log."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from simulator.loaders import day_input_paths

# Delivery times are sums of decimal distances, so they carry float noise
# (e.g. 557.1659999999999). This tolerance, the same one the simulator uses,
# stops a delivery exactly on a window edge from being misclassified.
TOLERANCE = 1e-9


def parse_time_to_minutes(time_str: str) -> int:
    """Convert an "HH:MM" string to minutes after midnight, e.g. "17:00" -> 1020."""
    hours, minutes = map(int, time_str.strip().split(":")[:2])
    return hours * 60 + minutes


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide, returning 0.0 instead of crashing when the denominator is zero."""
    return numerator / denominator if denominator > 0 else 0.0


def calculate_metrics(
    parcels: List[Dict[str, str]],
    distances: List[Dict[str, str]],
    config: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return on-time delivery metrics for one simulated day.

    Primary metric, on_time_delivery_rate:
        parcels delivered inside [delivery_window_start, delivery_window_end]
        divided by ALL parcels that day. Undelivered parcels count as misses,
        so a policy cannot score well by skipping hard parcels.
    on_time_rate_early_ok:
        the same, but early deliveries also count as on time.

    parcels and distances are the rows of the day's CSV files, config is the
    contents of config.json, and events are the records from the run's log.
    Parcel times are "HH:MM" strings; event times are minutes after midnight.
    """

    # 1. Delivery window (start, end) of every parcel, keyed by parcel_id
    windows = {}
    for p in parcels:
        windows[p["parcel_id"]] = (
            parse_time_to_minutes(p["delivery_window_start"]),
            parse_time_to_minutes(p["delivery_window_end"]),
        )

    # 2. From the log: when each parcel was delivered, and how many trips ran
    delivery_times = {}
    number_of_trips = 0
    for event in events:
        if event["event_type"] == "delivery":
            delivery_times.setdefault(event["parcel_id"], event["time"])
        elif event["event_type"] == "hub_departure":
            number_of_trips += 1

    # 3. Classify each delivered parcel as early, on time or late
    on_time = early = late = 0
    total_lateness = 0.0
    for pid, delivered_at in delivery_times.items():
        window_start, window_end = windows[pid]
        if delivered_at < window_start - TOLERANCE:
            early += 1
        elif delivered_at <= window_end + TOLERANCE:
            on_time += 1
        else:
            late += 1
            total_lateness += delivered_at - window_end

    # 4. Rates are measured against ALL parcels, so undelivered ones count as misses
    total_parcels = len(parcels)
    total_delivered = len(delivery_times)

    return {
        "total_parcels": total_parcels,
        "total_delivered": total_delivered,
        "undelivered_count": total_parcels - total_delivered,
        "on_time_deliveries": on_time,
        "early_deliveries": early,
        "late_deliveries": late,
        "on_time_delivery_rate": round(safe_divide(on_time, total_parcels), 4),
        "on_time_rate_early_ok": round(safe_divide(on_time + early, total_parcels), 4),
        "delivery_rate": round(safe_divide(total_delivered, total_parcels), 4),
        "mean_lateness_min": round(safe_divide(total_lateness, late), 2),
        "number_of_trips": number_of_trips,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Load one day's inputs and event log, then write the metrics report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"),
                        help="directory containing dist.csv, config.json and demand/")
    parser.add_argument("--day", required=True, help="day identifier, for example day_001")
    parser.add_argument("--log", type=Path, required=True,
                        help="event log from a simulator run")
    parser.add_argument("--output", type=Path,
                        help="JSON report (default: metrics.json beside the selected log)")
    args = parser.parse_args(argv)
    
    try:
        parcel_path, distance_path, config_path = day_input_paths(args.data, args.day)
        output = args.output if args.output is not None else args.log.with_name("metrics.json")
        # The input files all live in the data directory, so this also protects them.
        if output.resolve() == args.data.resolve() or args.data.resolve() in output.resolve().parents:
            raise ValueError("report output must be outside the input data directory")
        if output.resolve() == args.log.resolve():
            raise ValueError("report output must not overwrite the log")
        with parcel_path.open(newline="", encoding="utf-8-sig") as stream:
            parcels = list(csv.DictReader(stream))
        with distance_path.open(newline="", encoding="utf-8-sig") as stream:
            distances = list(csv.DictReader(stream))
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        with args.log.open(encoding="utf-8") as stream:
            events = [json.loads(line) for line in stream if line.strip()]
        metrics = calculate_metrics(parcels, distances, config, events)
        report = json.dumps(metrics, indent=2, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Metrics report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# def calculate_metrics(
#     parcels: List[Dict[str, str]],
#     distances: List[Dict[str, str]],
#     config: Dict[str, Any],
#     events: List[Dict[str, Any]],
# ) -> Dict[str, Any]:
#     """Return a JSON-serializable dictionary for the chosen performance metric.

#     parcels and distances are the rows of the day's CSV files, config is the
#     contents of config.json, and events are the records from the run's log.
#     CSV values are strings, so convert them before calculating. In particular,
#     parcel times are "HH:MM" strings while event times are minutes after
#     midnight: "17:00" is 17 * 60 = 1020.
#     """

#     # Illustration only: replace or extend this with your chosen metric.
#     number_of_trips = 0
#     for event in events:
#         if event["event_type"] == "hub_departure":
#             number_of_trips += 1
#     return {"number_of_trips": number_of_trips}


# def main(argv: Optional[List[str]] = None) -> int:
#     """Load one day's inputs and event log, then write the metrics report."""

#     parser = argparse.ArgumentParser(description=__doc__)
#     parser.add_argument("--data", type=Path, default=Path("data"),
#                         help="directory containing dist.csv, config.json and demand/")
#     parser.add_argument("--day", required=True, help="day identifier, for example day_001")
#     parser.add_argument("--log", type=Path, required=True,
#                         help="event log from a simulator run")
#     parser.add_argument("--output", type=Path,
#                         help="JSON report (default: metrics.json beside the selected log)")
#     args = parser.parse_args(argv)
#     try:
#         parcel_path, distance_path, config_path = day_input_paths(args.data, args.day)
#         output = args.output if args.output is not None else args.log.with_name("metrics.json")
#         # The input files all live in the data directory, so this also protects them.
#         if output.resolve() == args.data.resolve() or args.data.resolve() in output.resolve().parents:
#             raise ValueError("report output must be outside the input data directory")
#         if output.resolve() == args.log.resolve():
#             raise ValueError("report output must not overwrite the log")
#         with parcel_path.open(newline="", encoding="utf-8-sig") as stream:
#             parcels = list(csv.DictReader(stream))
#         with distance_path.open(newline="", encoding="utf-8-sig") as stream:
#             distances = list(csv.DictReader(stream))
#         config = json.loads(config_path.read_text(encoding="utf-8-sig"))
#         with args.log.open(encoding="utf-8") as stream:
#             events = [json.loads(line) for line in stream if line.strip()]
#         metrics = calculate_metrics(parcels, distances, config, events)
#         report = json.dumps(metrics, indent=2, allow_nan=False) + "\n"
#         output.parent.mkdir(parents=True, exist_ok=True)
#         output.write_text(report, encoding="utf-8")
#     except (OSError, ValueError) as exc:
#         parser.exit(2, f"error: {exc}\n")
#     print(f"Metrics report: {output}")
#     return 0


# if __name__ == "__main__":
#     raise SystemExit(main())
