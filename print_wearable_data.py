#!/usr/bin/env python3
"""
Script to print and explore wearable data from RA.json
Provides easy filtering by date range, IMEI, and metric.
"""

import json
import pandas as pd
from datetime import datetime, timedelta


def load_wearable_dataframe(json_path="RA.json"):
    """Load wearable data from JSON and return as DataFrame."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data['wearabledata'])

    # Convert datetime column
    df['record_datetime'] = pd.to_datetime(df['record_datetime'])

    # Convert value to numeric
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Sort by datetime
    df = df.sort_values('record_datetime').reset_index(drop=True)

    return df


def load_patients_dataframe(json_path="RA.json"):
    """Load patients data from JSON and return as DataFrame."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    patients_df = pd.DataFrame(data['patients'])
    return patients_df


def get_patient_imei(patient_id, json_path="RA.json"):
    """Get IMEI for a specific patient ID."""
    patients_df = load_patients_dataframe(json_path)
    patient = patients_df[patients_df['patient_id'] == str(patient_id)]

    if patient.empty:
        print(f"Warning: Patient {patient_id} not found!")
        return None

    return patient['imei'].iloc[0]


def print_wearable_data_by_patient(
    patient_id,
    date_start=None,
    date_end=None,
    metric=None,
    max_rows=50,
    show_stats=True
):
    """
    Print wearable data for a specific patient.

    Args:
        patient_id: Patient ID (e.g., '005', '456')
        date_start: Start date (str 'YYYY-MM-DD' or datetime object)
        date_end: End date (str 'YYYY-MM-DD' or datetime object)
        metric: Filter by specific metric (e.g., 'heart_rate', 'blood_oxygen_saturation')
        max_rows: Maximum rows to display (default 50, use None for all)
        show_stats: Show statistics summary (default True)

    Returns:
        Filtered DataFrame
    """
    # Get IMEI for the patient
    imei = get_patient_imei(patient_id)
    if imei is None:
        return None

    print(f"Patient {patient_id} uses device IMEI: {imei}\n")

    # Call the main function with the IMEI
    return print_wearable_data(
        date_start=date_start,
        date_end=date_end,
        imei=imei,
        metric=metric,
        max_rows=max_rows,
        show_stats=show_stats
    )


def print_wearable_data(
    df=None,
    date_start=None,
    date_end=None,
    imei=None,
    metric=None,
    max_rows=50,
    show_stats=True
):
    """
    Print wearable data with optional filtering.

    Args:
        df: DataFrame with wearable data (if None, will load from RA.json)
        date_start: Start date (str 'YYYY-MM-DD' or datetime object)
        date_end: End date (str 'YYYY-MM-DD' or datetime object)
        imei: Filter by specific IMEI
        metric: Filter by specific metric (e.g., 'heart_rate', 'blood_oxygen_saturation')
        max_rows: Maximum rows to display (default 50, use None for all)
        show_stats: Show statistics summary (default True)

    Returns:
        Filtered DataFrame
    """
    # Load data if not provided
    if df is None:
        print("Loading wearable data from RA.json...")
        df = load_wearable_dataframe()
        print(f"Loaded {len(df)} total records\n")

    # Apply filters
    filtered_df = df.copy()

    if date_start is not None:
        date_start = pd.to_datetime(date_start)
        filtered_df = filtered_df[filtered_df['record_datetime'] >= date_start]
        print(f"Filter: date >= {date_start}")

    if date_end is not None:
        date_end = pd.to_datetime(date_end)
        # Include the entire end day
        date_end = date_end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered_df = filtered_df[filtered_df['record_datetime'] <= date_end]
        print(f"Filter: date <= {date_end}")

    if imei is not None:
        filtered_df = filtered_df[filtered_df['imei'] == str(imei)]
        print(f"Filter: IMEI = {imei}")

    if metric is not None:
        filtered_df = filtered_df[filtered_df['metric'] == metric]
        print(f"Filter: metric = {metric}")

    print(f"\nFiltered results: {len(filtered_df)} records")
    print("=" * 80)

    # Show statistics
    if show_stats and len(filtered_df) > 0:
        print("\n--- STATISTICS ---")
        print(f"Date range: {filtered_df['record_datetime'].min()} to {filtered_df['record_datetime'].max()}")
        print(f"\nUnique IMEIs: {filtered_df['imei'].nunique()}")
        print(f"Unique metrics: {filtered_df['metric'].nunique()}")

        print("\nRecords per metric:")
        print(filtered_df['metric'].value_counts())

        print("\nRecords per IMEI:")
        print(filtered_df['imei'].value_counts())

        if metric is not None:
            print(f"\nValue statistics for {metric}:")
            print(filtered_df['value'].describe())

        print("=" * 80)

    # Display data
    print("\n--- DATA ---")
    pd.set_option('display.max_rows', max_rows)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    if max_rows is not None and len(filtered_df) > max_rows:
        print(f"Showing first {max_rows} of {len(filtered_df)} rows:")

    print(filtered_df)

    return filtered_df


def show_available_data_summary(df=None):
    """Show summary of available data in the dataset."""
    if df is None:
        df = load_wearable_dataframe()

    print("=" * 80)
    print("WEARABLE DATA SUMMARY")
    print("=" * 80)
    print(f"\nTotal records: {len(df):,}")
    print(f"Date range: {df['record_datetime'].min()} to {df['record_datetime'].max()}")
    print(f"\nUnique IMEIs: {df['imei'].nunique()}")
    print(f"Unique metrics: {df['metric'].nunique()}")

    print("\n--- AVAILABLE METRICS ---")
    metrics = df['metric'].value_counts()
    for metric, count in metrics.items():
        print(f"  {metric}: {count:,} records")

    print("\n--- AVAILABLE IMEIs ---")
    imeis = df['imei'].value_counts()
    for imei, count in imeis.items():
        print(f"  {imei}: {count:,} records")

    print("\n--- RECORDS PER DAY (last 10 days) ---")
    df['date'] = df['record_datetime'].dt.date
    daily = df.groupby('date').size().tail(10)
    for date, count in daily.items():
        print(f"  {date}: {count:,} records")

    print("=" * 80)


# ============================================================================
# EXAMPLES
# ============================================================================

if __name__ == '__main__':
    print("WEARABLE DATA EXPLORER\n")

    # Example 1: Show data summary
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Show complete data summary")
    print("=" * 80)
    show_available_data_summary()

    # Load data once for multiple queries
    df = load_wearable_dataframe()

    # Example 2: Show last 7 days of data
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Last 7 days of data (all metrics)")
    print("=" * 80)
    date_end = datetime.now()
    date_start = date_end - timedelta(days=7)
    print_wearable_data(
        df=df,
        date_start=date_start,
        date_end=date_end,
        max_rows=30
    )

    # Example 3: Specific date range and metric
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Heart rate data for January 20-25, 2026")
    print("=" * 80)
    print_wearable_data(
        df=df,
        date_start="2026-01-20",
        date_end="2026-01-25",
        metric="heart_rate",
        max_rows=40
    )

    # Example 4: Specific IMEI and metric
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Blood oxygen data for specific device")
    print("=" * 80)
    # Get first IMEI from the dataset
    first_imei = df['imei'].iloc[0]
    print_wearable_data(
        df=df,
        imei=first_imei,
        metric="blood_oxygen_saturation",
        date_start="2026-01-24",
        date_end="2026-01-26",
        max_rows=25
    )

    # Example 5: All data for one day
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: All metrics for January 25, 2026")
    print("=" * 80)
    print_wearable_data(
        df=df,
        date_start="2026-01-25",
        date_end="2026-01-25",
        max_rows=50
    )

    # Example 6: Query by patient ID
    print("\n\n" + "=" * 80)
    print("EXAMPLE 6: Patient 005 data from January 21-25, 2026")
    print("=" * 80)
    print_wearable_data_by_patient(
        patient_id="005",
        date_start="2026-01-21",
        date_end="2026-01-25",
        max_rows=30
    )

    print("\n\n" + "=" * 80)
    print("DONE! You can modify this script to explore different date ranges.")
    print("=" * 80)
