# Bank Customer Churn Analysis

## Project goal

This project examines which customer segments have higher observed churn rates
and turns a deliberately messy two-sheet workbook into a validated
customer-level dataset for analysis and Tableau reporting.

The project is designed as a descriptive business analysis, not a causal or
predictive model. Its main value is the reproducible path from raw data to
auditable findings.

## Tools

- Python and pandas for cleaning, validation, joining, and analysis
- Tableau for the interactive dashboard
- pytest-style data-quality tests

## Business questions

1. Which customer segments show the highest observed churn rates?
2. Do geography, age, activity, product count, or credit category reveal useful
   retention priorities?
3. Which findings are reliable enough to report, and which source fields should
   be excluded because of data-quality problems?

## Data workflow

1. Read `Customer_Info` and `Account_Info` from the raw Excel workbook.
2. Remove exact duplicate rows and validate one row per customer in each sheet.
3. Standardize geography labels (`FRA` and `French` become `France`).
4. Parse balance and salary currency strings.
5. Replace the invalid `-999999` salary sentinel with a missing value.
6. Validate that both sheets contain the same 10,000 customer IDs and matching
   tenure values.
7. Join the sheets one-to-one on `CustomerId`.
8. Create reusable age, balance, credit, activity, and product group fields.
9. Export the cleaned Tableau dataset, cleaning audit, KPI file, and segment
   summary.

## Important data-quality decision

The raw workbook's `HasCrCard` values duplicate `IsActiveMember` for every
customer. Because true credit-card status cannot be recovered from the messy
source, the pipeline keeps `HasCrCard` as missing for schema compatibility and
excludes it from analysis.

The pipeline also leaves three missing ages, surnames, and salaries as missing
rather than silently imputing them. Those customers remain in overall analyses;
the three missing ages are excluded only from age-segment calculations.

## Validation results

- Customer rows: **10,000**
- Unique customer IDs: **10,000**
- Exact duplicates removed: **1** from `Customer_Info`, **2** from
  `Account_Info`
- Tenure conflicts between sheets: **0**
- Missing/invalid age and salary records: **3**
- Standardized geographies: **France, Germany, Spain**

See [`cleaning_audit.json`](data/processed/cleaning_audit.json) for the full
machine-readable audit.

## Findings

The overall observed churn rate is **20.37%** (2,037 of 10,000 customers).

| Segment | Customers | Churned | Churn rate | Difference from overall |
|---|---:|---:|---:|---:|
| Three or more products | 326 | 280 | 85.89% | +65.52 pp |
| Age 51–60 | 797 | 448 | 56.21% | +35.84 pp |
| Germany | 2,509 | 814 | 32.44% | +12.07 pp |
| Inactive customers | 4,849 | 1,302 | 26.85% | +6.48 pp |
| Active customers | 5,151 | 735 | 14.27% | -6.10 pp |

The product-count result is the largest difference, but the three-or-more
product group contains only 326 customers. It should be investigated rather
than treated as proof that additional products cause churn. Germany and
inactivity are broader segments that may be practical starting points for
retention analysis.

Full counts and rates are in
[`analysis_summary.csv`](data/processed/analysis_summary.csv).

## Business recommendations

- Investigate the three-or-more product segment for product fit, fees, service
  issues, or selection effects before taking action.
- Compare customer journeys and service conditions in Germany with France and
  Spain.
- Test retention outreach for inactive customers and measure incremental
  outcomes against a control group.
- Add time-based behavior and contact history before making causal claims or
  deploying a churn model.

## Limitations

- This is a snapshot, so the analysis shows association rather than causation.
- Three records have no valid age or salary.
- Credit-card status is excluded because the raw field is unreliable.
- The dataset does not contain customer interactions, complaints, campaign
  exposure, or historical changes.

## Tableau dashboard

The supplied workbook visualizes churn by age group, product group, activity
status, credit category, and geography, with a gender filter. When opening it
on another computer, reconnect the workbook to
`data/processed/Bank_Churn_Cleaned.csv`.

#<img width="1296" height="744" alt="Screenshot 2026-07-11 at 12 23 38 PM" src="https://github.com/user-attachments/assets/53d4cc2d-466b-4c58-890b-68bb428415e3" />

## Repository structure

```text
data/
  raw/Bank_Churn_Messy.xlsx
  reference/Bank_Churn.csv
  reference/Bank_Churn_Data_Dictionary.csv
  processed/Bank_Churn_Cleaned.csv
  processed/analysis_summary.csv
  processed/cleaning_audit.json
  processed/kpis.json
src/
  clean_data.py
  analyze_churn.py
tests/
  test_data_quality.py
tableau/
  Tableau Bank Churn.twb
```

`Bank_Churn.csv` is retained only as a reference for row coverage. The pipeline
does not use it to fill missing or unreliable values from the messy workbook.

## Reproduce the analysis

```bash
python -m pip install -r requirements.txt
python src/clean_data.py
python src/analyze_churn.py
python -m pytest -q
```

## Skills demonstrated

- Raw-to-clean data pipelines
- Excel ingestion and one-to-one joins
- Data-quality validation and audit documentation
- Feature engineering for BI reporting
- Exploratory data analysis with sample sizes and rates
- Tableau dashboard development
- Translating findings into cautious business recommendations


