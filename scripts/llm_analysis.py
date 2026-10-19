#!/usr/bin/env python3
"""Optional OpenAI-compatible LLM analysis over a validated local evidence pack.

Keys are read only from the named environment variable. No data is transmitted
until the user explicitly runs this command against a configured endpoint.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence", type=Path, required=True, help="Validated JSON evidence pack")
    p.add_argument("--endpoint", default=os.environ.get("LLM_API_BASE_URL", ""), help="HTTPS OpenAI-compatible chat/completions URL")
    p.add_argument("--model", default=os.environ.get("LLM_MODEL", ""))
    p.add_argument("--api-key-env", default=os.environ.get("LLM_API_KEY_ENV", "LLM_API_KEY"), help="Environment variable name, never the secret itself")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    parsed = urlparse(a.endpoint)
    token = os.environ.get(a.api_key_env, "")
    if parsed.scheme != "https" or not parsed.netloc or not token or not a.model:
        p.error("configure an HTTPS endpoint, model, and API key in the named environment variable")
    try:
        evidence = json.loads(a.evidence.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict) or not (evidence.get("validation_passed") is True or evidence.get("passed") is True):
            p.error("evidence JSON must contain validation_passed: true or passed: true after local checks")
        prompt = ("Analyze only the supplied, validated evidence. Return Chinese Markdown with: "
                  "(1) data cutoff/source and missing fields, (2) observed structure and operational definitions, "
                  "(3) alternative explanations/counterevidence, (4) conditional scenarios with falsification conditions, "
                  "(5) separate factual values from analyst judgments. Do not invent prices, probability calibration, "
                  "or personalized buy/sell instructions. Mark every inference.\n\nEVIDENCE:\n" + json.dumps(evidence, ensure_ascii=False))
        body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(a.endpoint, data=body, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read(10 * 1024 * 1024).decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(content + "\n", encoding="utf-8")
        print(f"analysis saved: {a.out}; model output requires human/source review")
        return 0
    except (OSError, ValueError, KeyError, IndexError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"LLM analysis failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
