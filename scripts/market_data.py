#!/usr/bin/env python3
"""Import and audit licensed OHLCV data before Chan-structure analysis.

CSV is the portable default. An optional, user-configured HTTPS JSON endpoint is
supported with Bearer credentials read only from an environment variable.
This module does not include credentials or claim any provider authorization.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RAW_FIELDS = ("symbol", "date", "open", "high", "low", "close", "volume")
PRICE_FIELDS = ("open", "high", "low", "close")
OPTIONAL_FIELDS = ("amount", "adj_open", "adj_high", "adj_low", "adj_close", "adj_factor")
MAX_RESPONSE_BYTES = 50 * 1024 * 1024


class DataError(ValueError):
    pass


def _number(raw: Any, field: str, line: int, *, allow_zero: bool = True) -> float:
    try:
        value = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        raise DataError(f"line {line}: {field} is not numeric") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise DataError(f"line {line}: {field} must be finite")
    if value < 0 or (not allow_zero and value == 0):
        raise DataError(f"line {line}: {field} must be {'positive' if not allow_zero else 'non-negative'}")
    return value


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {h.strip() for h in (reader.fieldnames or [])}
        missing = set(RAW_FIELDS) - headers
        if missing:
            raise DataError("CSV missing columns: " + ", ".join(sorted(missing)))
        rows = []
        for line, row in enumerate(reader, start=2):
            item = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
            rows.append({"_line": line, **item})
    if not rows:
        raise DataError("CSV has no data rows")
    return rows


def audit_rows(rows: list[dict[str, Any]], *, source: str, adjustment: str,
               authorized: bool, fetched_at: str | None = None) -> dict[str, Any]:
    if adjustment not in {"raw", "forward", "backward", "vendor_adjusted"}:
        raise DataError("adjustment must be raw, forward, backward, or vendor_adjusted")
    if not source.strip():
        raise DataError("source/provider name is required")
    issues: list[dict[str, Any]] = []
    normalized = []
    seen: set[tuple[str, str]] = set()
    previous: dict[str, str] = {}
    for index, row in enumerate(rows):
        line = int(row.get("_line", index + 1))
        symbol = str(row.get("symbol", "")).strip()
        if not symbol:
            raise DataError(f"line {line}: symbol is empty")
        try:
            date = dt.date.fromisoformat(str(row.get("date", ""))[:10]).isoformat()
        except ValueError:
            raise DataError(f"line {line}: date must be ISO YYYY-MM-DD") from None
        key = (symbol, date)
        if key in seen:
            issues.append({"severity": "error", "line": line, "code": "duplicate_symbol_date", "date": date, "symbol": symbol})
        seen.add(key)
        if symbol in previous and date <= previous[symbol]:
            issues.append({"severity": "error", "line": line, "code": "date_not_strictly_ascending", "date": date, "symbol": symbol})
        previous[symbol] = date
        values = {name: _number(row.get(name), name, line, allow_zero=False) for name in PRICE_FIELDS}
        volume = _number(row.get("volume"), "volume", line)
        if values["high"] < max(values["open"], values["close"], values["low"]):
            issues.append({"severity": "error", "line": line, "code": "invalid_raw_high_low_order"})
        if values["low"] > min(values["open"], values["close"], values["high"]):
            issues.append({"severity": "error", "line": line, "code": "invalid_raw_low_high_order"})
        item: dict[str, Any] = {"symbol": symbol, "date": date, **values, "volume": volume, "source": source}
        for name in OPTIONAL_FIELDS:
            raw = row.get(name)
            if raw not in (None, ""):
                item[name] = _number(raw, name, line, allow_zero=(name not in {"adj_open", "adj_high", "adj_low", "adj_close", "adj_factor"}))
        adj_names = {"adj_open", "adj_high", "adj_low", "adj_close"}
        adj_present = adj_names.intersection(item)
        if adj_present and adj_present != adj_names:
            issues.append({"severity": "error", "line": line, "code": "partial_adjusted_ohlc"})
        if adj_present == adj_names:
            if item["adj_high"] < max(item["adj_open"], item["adj_close"], item["adj_low"]) or item["adj_low"] > min(item["adj_open"], item["adj_close"], item["adj_high"]):
                issues.append({"severity": "error", "line": line, "code": "invalid_adjusted_high_low_order"})
        if adjustment != "raw" and "adj_close" not in item:
            issues.append({"severity": "error", "line": line, "code": "adjusted_close_required_by_adjustment_mode"})
        if adjustment != "raw" and "adj_factor" not in item:
            issues.append({"severity": "error", "line": line, "code": "adjustment_factor_required_by_adjustment_mode"})
        if adjustment == "raw" and adj_present and not authorized:
            issues.append({"severity": "warning", "line": line, "code": "adjusted_values_without_authorization_attestation"})
        normalized.append(item)
    if any("adj_close" in row for row in normalized):
        if not all("adj_close" in row for row in normalized):
            issues.append({"severity": "error", "code": "mixed_adjusted_and_unadjusted_rows"})
        if not all("adj_factor" in row for row in normalized):
            issues.append({"severity": "warning", "code": "adjustment_factor_unavailable_or_incomplete"})
        else:
            factors = [r["adj_factor"] for r in normalized]
            base = factors[0]
            if base <= 0:
                issues.append({"severity": "error", "code": "invalid_adjustment_factor_base"})
            else:
                # Vendor factor scales can differ; ratios should nevertheless match adjusted/raw price ratios.
                implied_base = normalized[0]["adj_close"] / normalized[0]["close"]
                for i, (row, factor) in enumerate(zip(normalized, factors)):
                    implied = row["adj_close"] / row["close"]
                    scaled_factor = factor / base
                    implied_scaled = implied / implied_base
                    if abs(scaled_factor - implied_scaled) > max(0.0005, abs(implied_scaled) * 0.005):
                        issues.append({"severity": "error", "line": i + 1, "code": "adjustment_factor_close_ratio_mismatch", "factor_ratio": round(scaled_factor, 8), "close_ratio": round(implied_scaled, 8)})
    errors = sum(x["severity"] == "error" for x in issues)
    return {
        "schema_version": "1.0", "source": source, "source_authorized_by_user": bool(authorized),
        "adjustment": adjustment, "fetched_at_utc": fetched_at,
        "symbols": sorted({r["symbol"] for r in normalized}), "rows": len(normalized),
        "date_range": {"start": min(r["date"] for r in normalized), "end": max(r["date"] for r in normalized)},
        "adjusted_rows": sum("adj_close" in r for r in normalized), "factor_rows": sum("adj_factor" in r for r in normalized), "error_count": errors,
        "warning_count": len(issues) - errors, "passed": errors == 0 and authorized,
        "authorization_note": "User attested to provider/data license authorization; this tool does not independently verify the license." if authorized else "No authorization attestation; data must not be treated as licensed/authorized for downstream use.",
        "issues": issues,
    }


def _get_path(value: Any, dotted: str) -> Any:
    current = value
    for part in dotted.split(".") if dotted else []:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def fetch_json(config_path: Path) -> tuple[list[dict[str, Any]], str, str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    endpoint = str(config.get("endpoint", ""))
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise DataError("provider endpoint must be an HTTPS URL without embedded credentials")
    secret_env = str(config.get("api_key_env", "")).strip()
    token = os.environ.get(secret_env, "") if secret_env else ""
    if secret_env and not token:
        raise DataError(f"API credential not found in environment variable {secret_env}")
    headers = {"Accept": "application/json", "User-Agent": "mowna-thread-market-data/0.6"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(endpoint, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=min(max(int(config.get("timeout_seconds", 20)), 1), 60)) as response:
            if response.status != 200:
                raise DataError(f"provider returned HTTP {response.status}")
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.URLError as exc:
        raise DataError(f"provider request failed: {exc.reason}") from None
    if len(data) > MAX_RESPONSE_BYTES:
        raise DataError("provider response exceeds 50 MiB safety limit")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DataError("provider response is not valid UTF-8 JSON") from None
    records = _get_path(payload, str(config.get("rows_path", "data")))
    if not isinstance(records, list):
        raise DataError("rows_path must resolve to a JSON array")
    mapping = config.get("field_map", {})
    if not isinstance(mapping, dict):
        raise DataError("field_map must be a JSON object mapping canonical fields to provider fields")
    rows = []
    for record in records:
        if not isinstance(record, dict):
            raise DataError("provider rows must be JSON objects")
        rows.append({canonical: _get_path(record, provider_field) for canonical, provider_field in mapping.items()})
    return rows, str(config.get("provider_name", "user-configured provider")), dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Canonical OHLCV CSV input")
    parser.add_argument("--provider-config", type=Path, help="User-configured HTTPS JSON provider config")
    parser.add_argument("--source", default="", help="CSV data source/provider label")
    parser.add_argument("--adjustment", choices=("raw", "forward", "backward", "vendor_adjusted"), default="raw")
    parser.add_argument("--authorized", action="store_true", help="Attest you have rights to use this data from this provider")
    parser.add_argument("--out", type=Path, required=True, help="Audit JSON output")
    args = parser.parse_args()
    if bool(args.csv) == bool(args.provider_config):
        parser.error("specify exactly one of --csv or --provider-config")
    try:
        if args.csv:
            rows, source, fetched_at = load_csv(args.csv), args.source, None
        else:
            rows, source, fetched_at = fetch_json(args.provider_config)
            source = args.source or source
        report = audit_rows(rows, source=source, adjustment=args.adjustment, authorized=args.authorized, fetched_at=fetched_at)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"rows={report['rows']} symbols={len(report['symbols'])} errors={report['error_count']} warnings={report['warning_count']} passed={report['passed']} report={args.out}")
        return 0 if report["passed"] else 2
    except (DataError, OSError, json.JSONDecodeError) as exc:
        print(f"market data audit failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
