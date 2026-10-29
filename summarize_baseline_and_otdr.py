
import json
from pathlib import Path

policies = {
    "Baseline": Path("results/baseline"),
    "OTDR Greedy": Path("results/otdr"),
}

for policy, folder in policies.items():
    scores = []

    for day_num in range(1, 21):
        day = f"day_{day_num:03d}"
        metrics_file = folder / day / "metrics.json"

        if not metrics_file.exists():
            print(f"{policy}: Missing {day}/metrics.json")
            continue

        with metrics_file.open() as f:
            metrics = json.load(f)

        scores.append(metrics["on_time_delivery_rate"])

    print(f"\n{policy}")
    print(f"Days available: {len(scores)}/20")

    if scores:
        print(f"Average OTDR: {sum(scores) / len(scores):.2%}")
        print(f"Lowest OTDR:  {min(scores):.2%}")
        print(f"Highest OTDR: {max(scores):.2%}")
