
import csv
import json
from collections import defaultdict, Counter

day = "day_001"
target_locations = {"L017", "L032"}

with open(f"data/demand/{day}.csv", newline="") as f:
    parcels = {p["parcel_id"]: p for p in csv.DictReader(f)}

deliveries = defaultdict(list)

with open(f"results/otdr/{day}/log.txt") as f:
    for line in f:
        event = json.loads(line)

        if event["event_type"] != "delivery":
            continue

        pid = event["parcel_id"]
        location = parcels[pid]["delivery_location_id"]

        if location in target_locations:
            deliveries[location].append({
                "parcel_id": pid,
                "time": event["time"],
                "vehicle": event["vehicle_id"],
                "trip": event["trip_id"],
            })

for location in sorted(target_locations):
    print(f"\n{'=' * 45}")
    print(f"Location: {location}")

    records = deliveries[location]
    hourly = Counter(int(r["time"] // 60) for r in records)

    print(f"Total delivered: {len(records)}")
    print("Deliveries by hour:")
    for hour in sorted(hourly):
        print(f"  {hour:02d}:00–{hour:02d}:59: {hourly[hour]}")

    print("\nDelivered parcels:")
    for r in sorted(records, key=lambda x: x["time"]):
        hour = int(r["time"] // 60)
        minute = r["time"] % 60
        print(
            f"  {r['parcel_id']} | "
            f"{hour:02d}:{minute:05.2f} | "
            f"Vehicle {r['vehicle']} | Trip {r['trip']}"
        )
