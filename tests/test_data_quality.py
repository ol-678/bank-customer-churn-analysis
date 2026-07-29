"""Data-quality checks for the revised churn pipeline."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "Bank_Churn_Cleaned.csv"


def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def test_customer_grain_and_keys() -> None:
    df = load_data()
    assert len(df) == 10_000
    assert df["CustomerId"].nunique() == 10_000
    assert not df["CustomerId"].duplicated().any()


def test_valid_categories() -> None:
    df = load_data()
    assert set(df["Geography"]) == {"France", "Germany", "Spain"}
    assert set(df["Gender"]) == {"Female", "Male"}
    assert set(df["Exited"]) == {0, 1}
    assert set(df["IsActiveMember"]) == {0, 1}


def test_missing_values_are_intentional() -> None:
    df = load_data()
    assert df["Surname"].isna().sum() == 3
    assert df["Age"].isna().sum() == 3
    assert df["EstimatedSalary"].isna().sum() == 3
    assert df["HasCrCard"].isna().all()


def test_key_metrics() -> None:
    df = load_data()
    assert df["Exited"].sum() == 2_037
    assert round(df["Exited"].mean(), 4) == 0.2037
    geography = df.groupby("Geography")["Exited"].mean()
    assert round(geography["Germany"], 4) == 0.3244
    activity = df.groupby("ActivityStatus")["Exited"].mean()
    assert round(activity["Inactive"], 4) == 0.2685
    assert round(activity["Active"], 4) == 0.1427


def test_engineered_fields() -> None:
    df = load_data()
    assert df["AgeGroup"].notna().sum() == 9_997
    assert set(df["ProductGroup"]) == {"1", "2", "Three+"}
    assert not df["ProductGroup"].astype(str).str.contains(r"^\s|\s$").any()
