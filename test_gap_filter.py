"""
Test script to verify the 15-minute gap detection filter
"""
import pandas as pd
from src.data_loader import get_filtered_data
import src.config as config

# Test configuration - broader range to find gaps
imei_objetivo = config.IMEI["519"]
date_start = '2025-12-30 00:00:00'
date_end = '2025-12-31 23:59:59'
metric = "heart_rate"

print("=" * 80)
print("Testing Gap Detection Filter (15-minute threshold)")
print("=" * 80)

# Get filtered data
df = get_filtered_data(imei_objetivo, metric, date_start, date_end)

print(f"\nMetric: {metric}")
print(f"IMEI: {imei_objetivo}")
print(f"Date range: {date_start} to {date_end}")
print(f"Total data points (including NaN gaps): {len(df)}")

# Analyze gaps
if len(df) > 1:
    df_copy = df.copy()
    df_copy['time_diff'] = df_copy['record_datetime'].diff()

    # Count NaN values inserted by gap filter
    nan_count = df_copy['value'].isna().sum()
    print(f"\nNaN values inserted (line breaks): {nan_count}")

    # Show time differences
    print("\n" + "=" * 80)
    print("Time Differences Between Consecutive Points")
    print("=" * 80)

    # Show all gaps > 15 minutes
    gaps_df = df_copy[df_copy['time_diff'] > pd.Timedelta(minutes=15)]

    if len(gaps_df) > 0:
        print(f"\nFound {len(gaps_df)} gaps > 15 minutes:")
        print("-" * 80)
        for idx, row in gaps_df.iterrows():
            if idx > 0:
                prev_time = df_copy.loc[idx-1, 'record_datetime']
                curr_time = row['record_datetime']
                time_gap = row['time_diff']

                print(f"\nGap #{len(gaps_df[gaps_df.index <= idx])}:")
                print(f"  Previous point: {prev_time}")
                print(f"  Current point:  {curr_time}")
                print(f"  Gap duration:   {time_gap}")
                print(f"  Value at gap:   {row['value']} (should be None/NaN)")
    else:
        print("\nNo gaps > 15 minutes found in this dataset.")

    # Show first 20 rows for inspection
    print("\n" + "=" * 80)
    print("First 20 Data Points (for inspection)")
    print("=" * 80)
    print(df_copy[['record_datetime', 'value', 'time_diff']].head(20).to_string())

    # Show statistics
    print("\n" + "=" * 80)
    print("Statistics")
    print("=" * 80)
    print(f"Min value: {df['value'].min():.2f}" if not df['value'].isna().all() else "Min value: N/A")
    print(f"Max value: {df['value'].max():.2f}" if not df['value'].isna().all() else "Max value: N/A")
    print(f"Mean value: {df['value'].mean():.2f}" if not df['value'].isna().all() else "Mean value: N/A")
    print(f"Valid data points: {df['value'].notna().sum()}")
    print(f"NaN/Gap markers: {df['value'].isna().sum()}")

else:
    print("\nInsufficient data for gap analysis.")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
