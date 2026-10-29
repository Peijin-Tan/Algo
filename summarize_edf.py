
import json
from pathlib import Path

results_dir = Path("results/edf")
scores = []

print("EDF Results Across 20 Days")
print("-" * 35)

for day_num in range(1, 21):
    day = f"day_{day_num:03d}"
    metrics_file = results_dir / day / "metrics.json"

    if not metrics_file.exists():
        print(f"{day}: MISSING RESULTS")
        continue

    with metrics_file.open() as f:
        metrics = json.load(f)

    score = metrics["on_time_delivery_rate"]
    scores.append(score)
    print(f"{day}: {score:.2%}")

print("-" * 35)

if len(scores) == 20:
    print(f"Average OTDR: {sum(scores) / len(scores):.2%}")
    print(f"Lowest OTDR:  {min(scores):.2%}")
    print(f"Highest OTDR: {max(scores):.2%}")
else:
    print(f"Only {len(scores)} of 20 days have results.")
