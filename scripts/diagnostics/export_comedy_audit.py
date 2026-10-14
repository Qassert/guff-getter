"""Export the local comedy JSONL audit as one readable Markdown or CSV file."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from newsmuncher.services.comedy_audit import DEFAULT_AUDIT_PATH


def load_records(path):
    records = []
    with Path(path).open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on audit line {number}") from exc
    return records


def export_markdown(records, destination):
    dates = [record.get("timestamp", "") for record in records if record.get("timestamp")]
    flags = {}
    for record in records:
        for key, value in record.get("feature_flags", {}).items():
            flags.setdefault(key, set()).add(str(value))
    lines = ["# NewsMuncher comedy audit", "", f"Total MUNGEs: {len(records)}",
             f"Date range: {min(dates) if dates else 'unavailable'} to {max(dates) if dates else 'unavailable'}",
             "", "## Feature flags", ""]
    lines += [f"- `{key}`: {', '.join(sorted(values))}" for key, values in sorted(flags.items())]
    for index, record in enumerate(records, 1):
        lines += ["", f"## {index}. {record.get('final', {}).get('headline', '(untitled)')}", "",
                  f"- Timestamp: {record.get('timestamp', '')}",
                  f"- Rewrite UUID: `{record.get('rewrite_id', '')}`", "",
                  "### Original source", "",
                  f"**{record.get('source', {}).get('headline', '')}**", "",
                  record.get("source", {}).get("description", ""), "",
                  record.get("source", {}).get("article_text", ""), "",
                  "### Final article", "", record.get("final", {}).get("article_text", ""), "",
                  "### Ingredient provenance", "", "```json",
                  json.dumps(record.get("ingredients", {}), ensure_ascii=False, indent=2), "```", "",
                  "### Semantic metadata", "", "```json",
                  json.dumps(record.get("semantic", {}), ensure_ascii=False, indent=2), "```"]
    Path(destination).write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_csv(records, destination):
    with Path(destination).open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=(
            "timestamp", "rewrite_id", "source_headline", "source_article",
            "final_headline", "final_article", "feature_flags", "ingredients", "semantic",
        ))
        writer.writeheader()
        for record in records:
            writer.writerow({
                "timestamp": record.get("timestamp", ""), "rewrite_id": record.get("rewrite_id", ""),
                "source_headline": record.get("source", {}).get("headline", ""),
                "source_article": record.get("source", {}).get("article_text", ""),
                "final_headline": record.get("final", {}).get("headline", ""),
                "final_article": record.get("final", {}).get("article_text", ""),
                "feature_flags": json.dumps(record.get("feature_flags", {}), ensure_ascii=False),
                "ingredients": json.dumps(record.get("ingredients", {}), ensure_ascii=False),
                "semantic": json.dumps(record.get("semantic", {}), ensure_ascii=False),
            })


def export(source, destination, output_format="markdown"):
    records = load_records(source)
    Path(destination).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    (export_markdown if output_format == "markdown" else export_csv)(records, destination)
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_AUDIT_PATH.with_name("comedy_audit_report.md"))
    parser.add_argument("--format", choices=("markdown", "csv"), default="markdown")
    args = parser.parse_args()
    count = export(args.input, args.output, args.format)
    print(f"Exported {count} completed MUNGEs to {args.output}")
