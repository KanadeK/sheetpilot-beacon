"""Measure deterministic core-audit latency over the committed samples."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time
from pathlib import Path

from sheetpilot_beacon.services.audit import audit_workbook


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def run_benchmark(samples_dir: Path, iterations: int) -> dict[str, object]:
    """Return machine, input, and latency evidence as a JSON-safe mapping."""

    if iterations < 1:
        raise ValueError("iterations must be positive")
    samples = sorted(samples_dir.glob("*.xlsx"))
    if not samples:
        raise FileNotFoundError(f"no .xlsx samples found in {samples_dir}")

    for sample in samples:
        audit_workbook(sample)

    timings: dict[str, list[float]] = {sample.name: [] for sample in samples}
    findings: dict[str, int] = {}
    formulas: dict[str, int] = {}
    for _ in range(iterations):
        for sample in samples:
            started = time.perf_counter()
            report = audit_workbook(sample)
            timings[sample.name].append((time.perf_counter() - started) * 1000)
            findings[sample.name] = len(report.issues)
            formulas[sample.name] = report.metrics.formula_cell_count

    results = []
    for sample in samples:
        observations = timings[sample.name]
        results.append(
            {
                "workbook": sample.name,
                "bytes": sample.stat().st_size,
                "formula_cells": formulas[sample.name],
                "findings": findings[sample.name],
                "median_ms": round(statistics.median(observations), 3),
                "p95_ms": round(_percentile_95(observations), 3),
                "max_ms": round(max(observations), 3),
            }
        )
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine() or "not exposed by host",
        "processor": platform.processor() or "not exposed by host",
        "iterations_per_workbook": iterations,
        "warmup_runs_per_workbook": 1,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-dir", type=Path, default=Path("examples"))
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    arguments = parser.parse_args()
    payload = run_benchmark(arguments.samples_dir, arguments.iterations)
    if arguments.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(
        f"Python {payload['python']} · {payload['platform']} · "
        f"{payload['iterations_per_workbook']} measured runs/workbook"
    )
    for result in payload["results"]:
        assert isinstance(result, dict)
        print(
            f"{result['workbook']}: {result['bytes']} bytes, "
            f"{result['formula_cells']} formulas, {result['findings']} findings, "
            f"median {result['median_ms']} ms, p95 {result['p95_ms']} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
