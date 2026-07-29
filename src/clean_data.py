"""Build a validated customer-level churn dataset from the messy workbook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "Bank_Churn_Messy.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "Bank_Churn_Cleaned.csv"
DEFAULT_AUDIT = PROJECT_ROOT / "data" / "processed" / "cleaning_audit.json"
DEFAULT_REFERENCE = PROJECT_ROOT / "data" / "reference" / "Bank_Churn.csv"


def parse_currency(series: pd.Series) -> pd.Series:
    """Convert currency-like text to numeric values."""
    cleaned = (
        series.astype("string")
        .str.replace(r"[€$£,\s]", "", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_geography(series: pd.Series) -> pd.Series:
    """Standardize known geography variants without guessing unknown values."""
    return series.astype("string").str.strip().replace(
        {"FRA": "France", "French": "France"}
    )


def map_yes_no(series: pd.Series) -> pd.Series:
    """Map Yes/No text to nullable integers."""
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.map({"yes": 1, "no": 0}).astype("Int64")


def add_analysis_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Create transparent, reusable fields for Tableau and EDA."""
    result = df.copy()
    result["AgeGroup"] = pd.cut(
        result["Age"],
        bins=[18, 30, 40, 50, 60, np.inf],
        labels=["18–30", "31–40", "41–50", "51–60", "60+"],
        include_lowest=True,
    )
    result["BalanceGroup"] = pd.cut(
        result["Balance"],
        bins=[-0.01, 0, 50_000, 100_000, 150_000, np.inf],
        labels=["0", "0–50K", "50K–100K", "100K–150K", "150K+"],
        include_lowest=True,
    )
    result["CreditCategory"] = pd.cut(
        result["CreditScore"],
        bins=[300, 580, 670, 740, 850],
        labels=["Poor", "Fair", "Good", "Excellent"],
        include_lowest=True,
    )
    result["ActivityStatus"] = result["IsActiveMember"].map(
        {0: "Inactive", 1: "Active"}
    )
    result["ProductGroup"] = np.where(
        result["NumOfProducts"].ge(3),
        "Three+",
        result["NumOfProducts"].astype("Int64").astype("string"),
    )
    return result


def build_dataset(
    input_path: Path,
    output_path: Path,
    audit_path: Path,
    reference_path: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Clean, validate, join, engineer fields, and export the project dataset."""
    customer_raw = pd.read_excel(input_path, sheet_name="Customer_Info")
    account_raw = pd.read_excel(input_path, sheet_name="Account_Info")

    customer = customer_raw.drop_duplicates().copy()
    account = account_raw.drop_duplicates().copy()

    if customer["CustomerId"].duplicated().any():
        raise ValueError("Customer_Info still contains duplicate CustomerId values.")
    if account["CustomerId"].duplicated().any():
        raise ValueError("Account_Info still contains duplicate CustomerId values.")

    customer["Geography"] = normalize_geography(customer["Geography"])
    customer["Surname"] = customer["Surname"].astype("string").str.strip()
    customer["Gender"] = customer["Gender"].astype("string").str.strip().str.title()
    customer["EstimatedSalary"] = parse_currency(customer["EstimatedSalary"])
    customer.loc[customer["EstimatedSalary"].lt(0), "EstimatedSalary"] = np.nan

    account["Balance"] = parse_currency(account["Balance"])
    account["IsActiveMember"] = map_yes_no(account["IsActiveMember"])
    parsed_card = map_yes_no(account["HasCrCard"])

    # The raw workbook repeats IsActiveMember in HasCrCard for every customer.
    # Because the true card status cannot be inferred, retain the column for
    # schema compatibility but mark it entirely missing and exclude it from EDA.
    card_duplicates_activity = parsed_card.equals(account["IsActiveMember"])
    if card_duplicates_activity:
        account["HasCrCard"] = pd.Series(
            pd.array([pd.NA] * len(account), dtype="Int64"),
            index=account.index,
        )
    else:
        account["HasCrCard"] = parsed_card

    customer_ids = set(customer["CustomerId"])
    account_ids = set(account["CustomerId"])
    if customer_ids != account_ids:
        raise ValueError("Customer and account sheets contain different CustomerIds.")

    tenure_check = customer[["CustomerId", "Tenure"]].merge(
        account[["CustomerId", "Tenure"]],
        on="CustomerId",
        suffixes=("_customer", "_account"),
        validate="one_to_one",
    )
    tenure_mismatches = int(
        tenure_check["Tenure_customer"].ne(tenure_check["Tenure_account"]).sum()
    )
    if tenure_mismatches:
        raise ValueError(f"Tenure disagrees for {tenure_mismatches} customers.")

    account = account.drop(columns="Tenure")
    merged = customer.merge(
        account,
        on="CustomerId",
        how="inner",
        validate="one_to_one",
    )
    merged = add_analysis_fields(merged)
    tableau_columns = [
        "CustomerId",
        "Surname",
        "CreditScore",
        "Geography",
        "Gender",
        "Age",
        "Tenure",
        "Balance",
        "NumOfProducts",
        "HasCrCard",
        "IsActiveMember",
        "EstimatedSalary",
        "Exited",
        "AgeGroup",
        "BalanceGroup",
        "CreditCategory",
        "ActivityStatus",
        "ProductGroup",
    ]
    merged = merged[tableau_columns]

    expected_geographies = {"France", "Germany", "Spain"}
    if set(merged["Geography"].dropna().unique()) != expected_geographies:
        raise ValueError("Unexpected geography values remain after normalization.")
    if not merged["Exited"].dropna().isin([0, 1]).all():
        raise ValueError("Exited must contain only 0/1 values.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    audit: dict[str, object] = {
        "source": input_path.name,
        "raw_rows": {
            "Customer_Info": int(len(customer_raw)),
            "Account_Info": int(len(account_raw)),
        },
        "exact_duplicates_removed": {
            "Customer_Info": int(len(customer_raw) - len(customer)),
            "Account_Info": int(len(account_raw) - len(account)),
        },
        "processed_rows": int(len(merged)),
        "unique_customer_ids": int(merged["CustomerId"].nunique()),
        "tenure_mismatches": tenure_mismatches,
        "missing_values": {
            column: int(count)
            for column, count in merged.isna().sum().items()
            if count
        },
        "geography_values": sorted(merged["Geography"].dropna().unique().tolist()),
        "has_credit_card": {
            "raw_column_duplicated_activity_status": card_duplicates_activity,
            "action": (
                "Set HasCrCard to missing and exclude it from analysis because "
                "the true values cannot be inferred from the messy workbook."
                if card_duplicates_activity
                else "Parsed Yes/No values."
            ),
        },
        "analysis_exclusions": {
            "HasCrCard": "Unreliable source field.",
            "AgeGroup": f"{int(merged['Age'].isna().sum())} records lack age.",
            "EstimatedSalary": (
                f"{int(merged['EstimatedSalary'].isna().sum())} invalid sentinel "
                "values were converted to missing."
            ),
        },
    }

    if reference_path and reference_path.exists():
        reference = pd.read_csv(reference_path)
        audit["reference_comparison_only"] = {
            "reference_rows": int(len(reference)),
            "reference_unique_customer_ids": int(reference["CustomerId"].nunique()),
            "shared_customer_ids": int(
                len(set(reference["CustomerId"]) & set(merged["CustomerId"]))
            ),
            "note": (
                "The reference file was used only to validate row coverage; it "
                "was not used to fill missing or unreliable raw values."
            ),
        }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return merged, audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    dataset, audit_report = build_dataset(
        args.input, args.output, args.audit, args.reference
    )
    print(f"Wrote {len(dataset):,} rows to {args.output}")
    print(f"Wrote cleaning audit to {args.audit}")
