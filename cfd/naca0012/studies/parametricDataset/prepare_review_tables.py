#!/usr/bin/env python3
"""Prepare pending exclusion and physical-review tables from Phase 2 QC.

The generated tables are queues, not approvals. Automated-QC failures are
proposed for exclusion, while QC-usable high-AoA/high-Re cases are proposed for
physical review. A human must provide the reviewer and evidence fields before
provenance reconciliation can resolve either disposition.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDS = ("case_id", "decision", "reviewer", "evidence", "notes")


def read_unique(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = row.get("case_id", "").strip()
            if not case_id or case_id in rows:
                raise ValueError(f"missing or duplicate case_id in {path}: {case_id!r}")
            rows[case_id] = row
    if not rows:
        raise ValueError(f"no cases in {path}")
    return rows


def prepare_tables(
    inventory: dict[str, dict[str, str]],
    summary: dict[str, dict[str, str]],
    summary_label: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if inventory.keys() != summary.keys():
        missing_qc = sorted(inventory.keys() - summary.keys())
        extra_qc = sorted(summary.keys() - inventory.keys())
        raise ValueError(
            f"inventory/QC case mismatch; missing QC={missing_qc[:5]}, extra QC={extra_qc[:5]}"
        )

    exclusions: list[dict[str, str]] = []
    reviews: list[dict[str, str]] = []
    for case_id in sorted(inventory):
        inv = inventory[case_id]
        qc = summary[case_id]
        if qc.get("status") != "usable":
            warning = qc.get("warnings", "").strip() or f"QC status={qc.get('status', '')}"
            exclusions.append({
                "case_id": case_id,
                "decision": "exclude",
                "reviewer": "",
                "evidence": summary_label,
                "notes": f"Pending human disposition; automated {qc.get('qc_version', 'QC')} warning: {warning}",
            })
            continue

        high_aoa = abs(float(inv["aoa_deg"])) >= 14.0
        high_re = float(inv["re"]) >= 8.0e6
        risks = "+".join(
            name for name, active in (("high_aoa", high_aoa), ("high_re", high_re))
            if active
        )
        if risks:
            reviews.append({
                "case_id": case_id,
                "decision": "",
                "reviewer": "",
                "evidence": "",
                "notes": (
                    f"Pending physical review ({risks}); inspect force/moment history, y+, "
                    "surface Cp/skin friction, and wake or separation evidence."
                ),
            })
    return exclusions, reviews


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("cases.csv"))
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--exclusions-out", type=Path, required=True)
    parser.add_argument("--reviews-out", type=Path, required=True)
    args = parser.parse_args()

    inventory = read_unique(args.inventory)
    summary = read_unique(args.summary)
    exclusions, reviews = prepare_tables(inventory, summary, str(args.summary))
    write_rows(args.exclusions_out, exclusions)
    write_rows(args.reviews_out, reviews)
    print(f"Wrote {len(exclusions)} pending exclusions to {args.exclusions_out}")
    print(f"Wrote {len(reviews)} pending physical reviews to {args.reviews_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
