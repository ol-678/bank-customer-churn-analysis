"""Create reproducible churn KPIs and segment summaries."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "Bank_Churn_Cleaned.csv"
SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_summary.csv"
KPI_PATH = PROJECT_ROOT / "data" / "processed" / "kpis.json"

SEGMENTS = [
    "Geography",
    "Gender",
    "AgeGroup",
    "ProductGroup",
    "ActivityStatus",
    "CreditCategory",
]


def segment_summary(
    df: pd.DataFrame, column: str, overall_rate: float
) -> pd.DataFrame:
    summary = (
        df.dropna(subset=[column])
        .groupby(column, observed=True)["Exited"]
        .agg(customer_count="size", churned_count="sum", churn_rate="mean")
        .reset_index()
        .rename(columns={column: "segment_value"})
    )
    summary.insert(0, "segment", column)
    summary["churn_rate"] = summary["churn_rate"].round(4)
    summary["pp_difference_from_overall"] = (
        (summary["churn_rate"] - overall_rate) * 100
    ).round(2)
    return summary


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    overall_rate = float(df["Exited"].mean())

    summaries = [
        segment_summary(df, column, overall_rate) for column in SEGMENTS
    ]
    analysis = pd.concat(summaries, ignore_index=True)
    analysis.to_csv(SUMMARY_PATH, index=False)

    kpis = {
        "customers": int(len(df)),
        "churned_customers": int(df["Exited"].sum()),
        "overall_churn_rate": round(overall_rate, 4),
        "age_available_customers": int(df["Age"].notna().sum()),
        "has_credit_card_included": False,
    }
    KPI_PATH.write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    print(f"Wrote {len(analysis):,} segment rows to {SUMMARY_PATH}")
    print(f"Wrote KPI summary to {KPI_PATH}")


if __name__ == "__main__":
    main()
