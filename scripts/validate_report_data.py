#!/usr/bin/env python3
"""Validate report evidence packs for traceability and numerical consistency."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def fail(errors):
    print("FAIL")
    for e in errors:
        print(f"- {e}")
    raise SystemExit(1)


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = []
    for key in ("schema_version", "report_id", "as_of", "sources", "metrics", "sections"):
        if key not in data:
            errors.append(f"missing top-level field: {key}")
    try:
        datetime.fromisoformat(data.get("as_of", "").replace("Z", "+00:00"))
    except ValueError:
        errors.append("as_of must be an ISO-8601 timestamp")
    sources = {s.get("id"): s for s in data.get("sources", [])}
    for sid, src in sources.items():
        if not sid or not re.match(r"^https?://", src.get("url", "")):
            errors.append(f"source {sid!r} needs id and http(s) URL")
        if not src.get("title") or not src.get("published_at"):
            errors.append(f"source {sid!r} needs title and published_at")
    metrics = {}
    metric_groups = {}
    for m in data.get("metrics", []):
        mid = m.get("id")
        if not mid or mid in metrics:
            errors.append(f"metric id missing or duplicated: {mid!r}")
        metrics[mid] = m
        if m.get("canonical_id"):
            metric_groups.setdefault(m["canonical_id"], []).append(m)
        for key in ("name", "value", "unit", "period_end", "source_id", "confidence"):
            if key not in m or m[key] in (None, ""):
                errors.append(f"metric {mid!r} missing {key}")
        try:
            float(m.get("value"))
        except (TypeError, ValueError):
            errors.append(f"metric {mid!r} value must be numeric")
        if m.get("source_id") not in sources:
            errors.append(f"metric {mid!r} references unknown source {m.get('source_id')!r}")
        if m.get("conflict_note") and data.get("conclusion_status") == "investment_view":
            errors.append(f"metric {mid!r} has unresolved conflict but report asserts investment_view")
    for canonical_id, group in metric_groups.items():
        units = {m.get("unit") for m in group}
        periods = {m.get("period_end") for m in group}
        if (len(units) > 1 or len(periods) > 1) and not all(m.get("normalized_value") is not None and m.get("normalized_unit") and m.get("normalized_period_end") for m in group):
            errors.append(f"canonical metric {canonical_id!r} mixes units/periods without normalized fields")
    for section in data.get("sections", []):
        for ref in section.get("metric_refs", []):
            if ref not in metrics:
                errors.append(f"section {section.get('title')!r} references unknown metric {ref!r}")
        for ref in section.get("source_refs", []):
            if ref not in sources:
                errors.append(f"section {section.get('title')!r} references unknown source {ref!r}")
    for chart in data.get("charts", []):
        if chart.get("source_id") and chart["source_id"] not in sources:
            errors.append(f"chart {chart.get('title')!r} references unknown source {chart['source_id']!r}")
        for ref in chart.get("metric_refs", []):
            if ref not in metrics:
                errors.append(f"chart {chart.get('title')!r} references unknown metric {ref!r}")
    for check in data.get("numeric_checks", []):
        mid = check.get("metric_id")
        if mid not in metrics:
            errors.append(f"numeric check references unknown metric {mid!r}")
            continue
        expected = float(metrics[mid]["value"])
        if check.get("operation") == "round":
            digits = int(check.get("digits", 2))
            computed = round(expected, digits)
        elif check.get("operation") == "multiply":
            computed = expected * float(check["factor"])
        else:
            errors.append(f"unsupported numeric check operation {check.get('operation')!r}")
            continue
        if abs(computed - float(check["expected"])) > float(check.get("tolerance", 1e-8)):
            errors.append(f"numeric check failed for {mid}: computed {computed}, expected {check['expected']}")
    pdf = data.get("rendered_pdf")
    if pdf:
        from pypdf import PdfReader
        p = Path(pdf)
        if not p.exists():
            errors.append(f"rendered PDF not found: {pdf}")
        else:
            reader = PdfReader(str(p))
            pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            for check in data.get("pdf_text_checks", []):
                if check not in pdf_text:
                    errors.append(f"PDF text check missing: {check!r}")
            uri_links = {a.get_object().get("/A", {}).get("/URI") for page in reader.pages for a in (page.get("/Annots") or []) if a.get_object().get("/A", {}).get("/URI")}
            for src in data.get("sources", []):
                if src["url"] not in uri_links:
                    errors.append(f"PDF source link not clickable/present: {src['id']}")
    text = json.dumps(data, ensure_ascii=False)
    for mid in re.findall(r"\{\{metric:([\w.-]+)\}\}", text):
        if mid not in metrics:
            errors.append(f"unresolved metric token: {mid}")
    if errors:
        fail(errors)
    print(f"PASS: {len(metrics)} metrics, {len(sources)} sources, {len(data.get('sections', []))} sections, {len(data.get('charts', []))} charts")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_report_data.py REPORT.json")
    main(sys.argv[1])
