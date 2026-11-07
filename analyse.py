"""
analyse.py
==========
A tiny optional helper that summarises results.csv after a session.

It is not needed to run the experiments - it simply prints averages so the data
can be pasted into the report.  Run it in the same folder as results.csv:

    python analyse.py

Because Fitts' law uses the index of difficulty, the table also shows
ID = log2(distance / target_size + 1) for every distance/size combination.
"""

import math
from collections import defaultdict

import logger


def mean(values):
    """Average of a list of numbers (0 when the list is empty)."""
    return sum(values) / len(values) if values else 0.0


def main():
    """Read results.csv and print three short summary tables."""
    rows = logger.read_results()
    if not rows:
        print("results.csv does not exist yet, or it is still empty.")
        print("Run a task in the app first.")
        return

    print(f"{len(rows)} rows in results.csv\n")

    # -- table 1: one line per participant and task ------------------------
    print("Average time and ease of use per participant / task")
    print("-" * 64)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["participant_id"], row["task_type"])].append(row)
    for (participant, task), group in sorted(grouped.items()):
        times = [float(r["time_taken_seconds"]) for r in group if r["time_taken_seconds"]]
        ratings = [int(r["ease_of_use"]) for r in group if r["ease_of_use"]]
        print(f"  {participant:<8} {task:<16} n={len(group):<3} "
              f"avg time={mean(times):.3f}s  avg ease={mean(ratings):.2f}")

    # -- table 2: the visual condition effect ------------------------------
    print("\nAverage time per visual condition")
    print("-" * 64)
    by_condition = defaultdict(list)
    for row in rows:
        if row["time_taken_seconds"]:
            by_condition[row["visual_condition"]].append(float(row["time_taken_seconds"]))
    for condition, times in sorted(by_condition.items()):
        print(f"  {condition:<48} {mean(times):.3f}s  (n={len(times)})")

    # -- table 3: Fitts' law -------------------------------------------------
    hitting = [r for r in rows if r["task_type"] == "Target Hitting"]
    if hitting:
        print("\nFitts' law: average time per distance / target size")
        print("-" * 64)
        print("  distance   size   ID      avg time   errors")
        cells = defaultdict(list)
        for row in hitting:
            key = (float(row["target_distance_px"]), float(row["target_size_px"]))
            cells[key].append(row)
        for (distance, size), group in sorted(cells.items()):
            times = [float(r["time_taken_seconds"]) for r in group if r["time_taken_seconds"]]
            errors = [int(r["error_count"]) for r in group if r["error_count"]]
            difficulty = math.log2(distance / size + 1)
            print(f"  {distance:>7.0f}  {size:>5.0f}   {difficulty:.2f}   "
                  f"{mean(times):>7.3f}s   {mean(errors):.2f}")

        print("\nFitts' law predicts that time grows with ID (bits).  Sorting the")
        print("rows above by ID should show a roughly straight line.")


if __name__ == "__main__":
    main()
