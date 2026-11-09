"""
Run Comparison Script for GraphRAG-1 Evaluation V2
Usage:
  python graph/evaluation_v2/compare_runs.py <runA> <runB>
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = BASE_DIR / "graph" / "evaluation_v2" / "runs"


def resolve_run_dir(path_str: str) -> Path:
    p = Path(path_str)
    if p.exists() and p.is_dir():
        return p
    # Check inside RUNS_DIR
    p2 = RUNS_DIR / path_str
    if p2.exists() and p2.is_dir():
        return p2
    raise FileNotFoundError(f"Run directory not found: {path_str}")


def format_delta(valA: float, valB: float, is_percentage: bool = True) -> str:
    diff = valB - valA
    if is_percentage:
        sign = "+" if diff > 0 else ""
        return f"{valB * 100:.1f}% ({sign}{diff * 100:.1f}%)"
    else:
        sign = "+" if diff > 0 else ""
        return f"{valB:.2f}s ({sign}{diff:.2f}s)"


def main():
    if len(sys.argv) < 3:
        print("Usage: python graph/evaluation_v2/compare_runs.py <runA> <runB>")
        sys.exit(1)

    dirA = resolve_run_dir(sys.argv[1])
    dirB = resolve_run_dir(sys.argv[2])

    summaryA_path = dirA / "summary.json"
    summaryB_path = dirB / "summary.json"

    if not summaryA_path.exists():
        print(f"Error: {summaryA_path} does not exist.")
        sys.exit(1)
    if not summaryB_path.exists():
        print(f"Error: {summaryB_path} does not exist.")
        sys.exit(1)

    with open(summaryA_path, "r", encoding="utf-8") as f:
        sumA = json.load(f)
    with open(summaryB_path, "r", encoding="utf-8") as f:
        sumB = json.load(f)

    print(f"# Benchmark Comparison: `{dirA.name}` vs `{dirB.name}`\n")
    print("## 1. Overall System Comparison")
    print(f"| Metric | Run A (`{dirA.name}`) | Run B (`{dirB.name}`) | Delta (B - A) |")
    print("| :--- | :---: | :---: | :---: |")
    print(f"| **Mode** | {sumA.get('mode')} | {sumB.get('mode')} | — |")
    print(f"| **Total Cases** | {sumA.get('total_cases')} | {sumB.get('total_cases')} | {sumB.get('total_cases', 0) - sumA.get('total_cases', 0)} |")
    print(f"| **Valid Cases** | {sumA.get('valid_cases')} | {sumB.get('valid_cases')} | {sumB.get('valid_cases', 0) - sumA.get('valid_cases', 0)} |")
    print(f"| **Infra Errors** | {sumA.get('infra_errors')} | {sumB.get('infra_errors')} | {sumB.get('infra_errors', 0) - sumA.get('infra_errors', 0)} |")

    # Latency
    p50_A = sumA.get("latency_p50", 0.0)
    p50_B = sumB.get("latency_p50", 0.0)
    p95_A = sumA.get("latency_p95", 0.0)
    p95_B = sumB.get("latency_p95", 0.0)
    print(f"| **Latency p50** | {p50_A:.2f}s | {p50_B:.2f}s | {p50_B - p50_A:+.2f}s |")
    print(f"| **Latency p95** | {p95_A:.2f}s | {p95_B:.2f}s | {p95_B - p95_A:+.2f}s |")

    # Metrics
    metA = sumA.get("overall_metrics", {})
    metB = sumB.get("overall_metrics", {})
    all_metrics = sorted(set(metA.keys()).union(set(metB.keys())))

    for m in all_metrics:
        valA = metA.get(m)
        valB = metB.get(m)
        if valA is not None and valB is not None:
            is_pct = "recall" in m or "precision" in m or "exact" in m or "accuracy" in m or "free" in m
            diff = valB - valA
            sign = "+" if diff > 0 else ""
            if is_pct:
                strA = f"{valA * 100:.1f}%"
                strB = f"{valB * 100:.1f}%"
                strD = f"{sign}{diff * 100:.1f}%"
            else:
                strA = f"{valA:.2f}"
                strB = f"{valB:.2f}"
                strD = f"{sign}{diff:.2f}"
            print(f"| **{m}** | {strA} | {strB} | **{strD}** |")

    print("\n## 2. Metrics Delta by Query Type")
    typesA = sumA.get("by_type", {})
    typesB = sumB.get("by_type", {})
    all_types = sorted(set(typesA.keys()).union(set(typesB.keys())))

    common_metrics = [m for m in ["node_recall", "field_recall", "intent_accuracy", "answer_exact"] if any(m in typesA.get(t, {}) or m in typesB.get(t, {}) for t in all_types)]

    header_cols = ["Query Type", "Count A -> B"] + [f"{m} Δ" for m in common_metrics]
    print(f"| {' | '.join(header_cols)} |")
    print(f"| {':--- | ' + ' | '.join([':---:' for _ in header_cols[1:]])} |")

    for qt in all_types:
        rowA = typesA.get(qt, {})
        rowB = typesB.get(qt, {})
        cntA = rowA.get("count", 0)
        cntB = rowB.get("count", 0)
        row_str = [f"`{qt}`", f"{cntA} -> {cntB}"]

        for m in common_metrics:
            vA = rowA.get(m)
            vB = rowB.get(m)
            if vA is not None and vB is not None:
                d = vB - vA
                sign = "+" if d > 0 else ""
                row_str.append(f"{vB*100:.1f}% ({sign}{d*100:.1f}%)")
            elif vB is not None:
                row_str.append(f"{vB*100:.1f}% (new)")
            elif vA is not None:
                row_str.append(f"{vA*100:.1f}% (absent)")
            else:
                row_str.append("—")

        print(f"| {' | '.join(row_str)} |")


if __name__ == "__main__":
    main()

