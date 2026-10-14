#!/usr/bin/env python3
"""Export Phase 4K audit records for blind, offline human comparison."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random


def load_records(path):
    records = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("comparison_variant") in {"A", "B", "C", "D"}:
                records.append(record)
    return records


def export(source, output, key_output, seed="phase4k-blind"):
    records = load_records(source)
    rng = random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big"))
    output, key_output = Path(output), Path(key_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    lines = ["# NewsMuncher blind comedy comparison", "",
             f"Outputs: {len(records)}", "",
             "Score each output for humour, surprise, coherence, source relevance, "
             "British absurdity and repetition before opening the key file.", ""]
    groups = {}
    for record in records:
        source_id = record.get("experiment_source_id") or record.get("source", {}).get("headline", "")
        groups.setdefault(source_id, []).append(record)
    for article_index, source_id in enumerate(sorted(groups), 1):
        versions = list(groups[source_id]); rng.shuffle(versions)
        source_data = versions[0].get("source", {})
        lines += [f"## Article {article_index}", "", "### Original source", "",
                  f"**{source_data.get('headline', '')}**", "",
                  source_data.get("article_text", ""), ""]
        for version_index, record in enumerate(versions, 1):
            label = f"Article {article_index} — Version {version_index}"
            final = record.get("final", {})
            lines += [f"### {label}", "", f"**{final.get('headline', '')}**", "",
                      final.get("article_text", ""), ""]
            rows.append({"output": label, "variant": record["comparison_variant"],
                         "rewrite_id": record.get("rewrite_id", ""),
                         "source_id": source_id,
                         "source_headline": source_data.get("headline", "")})
    output.write_text("\n".join(lines), encoding="utf-8")
    with key_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else
                                ("output", "variant", "rewrite_id", "source_headline"))
        writer.writeheader(); writer.writerows(rows)
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default="local_audits/comedy_audit.jsonl")
    parser.add_argument("--output", default="local_audits/comedy_phase4k_blind.md")
    parser.add_argument("--key-output", default="local_audits/comedy_phase4k_key.csv")
    parser.add_argument("--seed", default="phase4k-blind")
    args = parser.parse_args()
    count = export(args.source, args.output, args.key_output, args.seed)
    print(f"Exported {count} outputs to {args.output}; key: {args.key_output}")


if __name__ == "__main__":
    main()
