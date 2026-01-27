#!/usr/bin/env python3
"""
Example: Print wearable data for Patient 005 from January 21-25, 2026
"""

from print_wearable_data import print_wearable_data_by_patient

# Method 1: Using the convenience function (easiest!)
print("=" * 80)
print("PATIENT 005 DATA - January 21-25, 2026")
print("=" * 80)
print()

result = print_wearable_data_by_patient(
    patient_id="005",
    date_start="2026-01-21",
    date_end="2026-01-25",
    max_rows=100  # Show first 100 rows
)

# You can also filter by specific metric
print("\n\n" + "=" * 80)
print("PATIENT 005 - HEART RATE ONLY")
print("=" * 80)
print()

result_hr = print_wearable_data_by_patient(
    patient_id="005",
    date_start="2026-01-21",
    date_end="2026-01-25",
    metric="heart_rate",
    max_rows=50
)

# The result is a pandas DataFrame, you can use it for further analysis
if result_hr is not None:
    print("\n\nQuick stats:")
    print(f"Average heart rate: {result_hr['value'].mean():.1f} bpm")
    print(f"Min heart rate: {result_hr['value'].min():.1f} bpm")
    print(f"Max heart rate: {result_hr['value'].max():.1f} bpm")
