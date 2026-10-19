#!/usr/bin/env python3
"""Causal candidate Chan-style annotations for already-audited OHLCV CSV.

This is one explicit operationalization, not a claim that all Chan schools use
the same definitions. Fractals and strokes are confirmed only when observable.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from typing import Any
try:
    from .market_data import DataError, load_csv, audit_rows
except ImportError:  # direct script execution
    from market_data import DataError, load_csv, audit_rows


def annotate(rows: list[dict[str, Any]], *, source: str, authorized: bool,
             minimum_stroke_bars: int = 4) -> dict[str, Any]:
    audit = audit_rows(rows, source=source, adjustment="raw", authorized=authorized)
    if not audit["passed"]:
        raise DataError("input audit must pass with user authorization before annotation")
    if len(audit["symbols"]) != 1:
        raise DataError("annotation accepts exactly one symbol per file; split multi-symbol datasets first")
    # Merge inclusive bars using the prior movement direction; keep source-row ranges.
    merged: list[dict[str, Any]] = []
    direction = 0
    for i, raw in enumerate(rows):
        bar = {"date": str(raw["date"])[:10], "high": float(raw["high"]), "low": float(raw["low"]), "first": i, "last": i}
        if merged and ((bar["high"] <= merged[-1]["high"] and bar["low"] >= merged[-1]["low"]) or (bar["high"] >= merged[-1]["high"] and bar["low"] <= merged[-1]["low"])):
            prev = merged[-1]
            if direction >= 0:
                prev["high"] = max(prev["high"], bar["high"])
                prev["low"] = max(prev["low"], bar["low"])
            else:
                prev["high"] = min(prev["high"], bar["high"])
                prev["low"] = min(prev["low"], bar["low"])
            prev["last"] = i
        else:
            if merged:
                direction = 1 if bar["high"] > merged[-1]["high"] and bar["low"] > merged[-1]["low"] else -1
            merged.append(bar)
    candidates = []
    for i in range(1, len(merged) - 1):
        left, mid, right = merged[i - 1], merged[i], merged[i + 1]
        top = mid["high"] > left["high"] and mid["high"] > right["high"] and mid["low"] > left["low"] and mid["low"] > right["low"]
        bottom = mid["high"] < left["high"] and mid["high"] < right["high"] and mid["low"] < left["low"] and mid["low"] < right["low"]
        if top or bottom:
            candidates.append({"kind": "top" if top else "bottom", "pivot_date": mid["date"], "confirmed_at": right["date"], "price": mid["high"] if top else mid["low"], "merged_index": i, "source_bar_index": mid["last"]})
    # Require alternating pivots. Replace same-side candidates only with more extreme ones.
    extrema = []
    for item in candidates:
        if not extrema:
            extrema.append(item)
        elif extrema[-1]["kind"] == item["kind"]:
            more_extreme = item["price"] > extrema[-1]["price"] if item["kind"] == "top" else item["price"] < extrema[-1]["price"]
            if more_extreme:
                extrema[-1] = item
        else:
            extrema.append(item)
    strokes = []
    for left, right in zip(extrema, extrema[1:]):
        span = right["merged_index"] - left["merged_index"]
        if span >= minimum_stroke_bars:
            strokes.append({"index": len(strokes) + 1, "direction": "up" if right["kind"] == "top" else "down", "from_date": left["pivot_date"], "to_date": right["pivot_date"], "confirmed_at": right["confirmed_at"], "start": left["price"], "end": right["price"], "merged_bar_span": span})
    zones = []
    # Candidate 3-stroke overlap only. Rolling, non-overlapping zones are intentionally not inferred.
    for i in range(2, len(strokes)):
        triple = strokes[i - 2:i + 1]
        ranges = [(min(x["start"], x["end"]), max(x["start"], x["end"])) for x in triple]
        lower, upper = max(x[0] for x in ranges), min(x[1] for x in ranges)
        if lower < upper:
            zones.append({"type": "candidate_three_stroke_overlap", "from_date": triple[0]["from_date"], "to_date": triple[-1]["to_date"], "confirmed_at": triple[-1]["confirmed_at"], "lower": lower, "upper": upper})
    return {"schema_version": "1.0", "method": "inclusive-bar merge; strict 3-bar fractal; alternating extrema; minimum merged-bar stroke span; rolling 3-stroke overlap", "status": "candidate_only", "lookahead_policy": "fractal confirmation date is the right-hand bar; a stroke is available only on its endpoint fractal confirmation date", "limitations": ["Operationalization is configurable and not a universal/original canonical interpretation.", "No intraday/intra-bar sequencing, volume confirmation, segment/central-zone completion, trading signal, or return claim.", "Corporate actions must be handled upstream; this tool accepts raw OHLCV only."], "source_authorized_by_user": bool(authorized), "rows": len(rows), "merged_bars": len(merged), "fractals": candidates, "strokes": strokes, "candidate_zones": zones}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--authorized", action="store_true")
    p.add_argument("--minimum-stroke-bars", type=int, default=4)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.minimum_stroke_bars < 2:
        p.error("--minimum-stroke-bars must be >= 2")
    try:
        result = annotate(load_csv(a.csv), source=a.source, authorized=a.authorized, minimum_stroke_bars=a.minimum_stroke_bars)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"fractals={len(result['fractals'])} strokes={len(result['strokes'])} zones={len(result['candidate_zones'])} output={a.out}")
        return 0
    except (DataError, OSError) as exc:
        p.exit(2, f"annotation refused: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
