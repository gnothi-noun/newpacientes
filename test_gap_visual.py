"""
Visual test to see how gap detection affects line graphs
"""
import matplotlib.pyplot as plt
import pandas as pd
from src.data_loader import get_filtered_data
import src.config as config

# Test configuration
imei_objetivo = config.IMEI["519"]
date_start = '2025-12-30 09:00:00'  # Focus on the area with the gap
date_end = '2025-12-30 10:00:00'
metric = "heart_rate"

print("Generating visual comparison of gap detection filter...")

# Get filtered data (with gap detection)
df_with_gaps = get_filtered_data(imei_objetivo, metric, date_start, date_end)

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Plot 1: With gap detection (line breaks at gaps)
ax1.plot(df_with_gaps['record_datetime'], df_with_gaps['value'],
         'b-o', linewidth=2, markersize=4, label='Heart Rate')
ax1.set_title('WITH Gap Detection Filter (Line breaks at >15min gaps)',
              fontsize=14, fontweight='bold')
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Heart Rate (bpm)', fontsize=12)
ax1.grid(True, alpha=0.3)
ax1.legend()

# Add annotations for NaN points
nan_points = df_with_gaps[df_with_gaps['value'].isna()]
for idx, row in nan_points.iterrows():
    ax1.axvline(x=row['record_datetime'], color='red', linestyle='--',
                alpha=0.7, linewidth=1.5, label='Gap Marker' if idx == nan_points.index[0] else '')
    ax1.text(row['record_datetime'], ax1.get_ylim()[1] * 0.95,
             'GAP >15min', rotation=90, verticalalignment='top',
             color='red', fontweight='bold')

# Plot 2: Highlight the gap with annotations
ax2.plot(df_with_gaps['record_datetime'], df_with_gaps['value'],
         'g-o', linewidth=2, markersize=6)
ax2.set_title('Close-up View Showing Gap Detection',
              fontsize=14, fontweight='bold')
ax2.set_xlabel('Time', fontsize=12)
ax2.set_ylabel('Heart Rate (bpm)', fontsize=12)
ax2.grid(True, alpha=0.3)

# Add gap information
if len(nan_points) > 0:
    gap_info = f"Gaps detected: {len(nan_points)}\nLine discontinuities: {len(nan_points)}"
    ax2.text(0.02, 0.98, gap_info, transform=ax2.transAxes,
             fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.savefig('gap_detection_test.png', dpi=150, bbox_inches='tight')
print(f"\n[OK] Graph saved as 'gap_detection_test.png'")

# Print detailed info
print("\n" + "="*80)
print("Gap Detection Summary")
print("="*80)
print(f"Time range: {date_start} to {date_end}")
print(f"Metric: {metric}")
print(f"Total points: {len(df_with_gaps)}")
print(f"Valid data points: {df_with_gaps['value'].notna().sum()}")
print(f"Gap markers (NaN): {df_with_gaps['value'].isna().sum()}")

if len(nan_points) > 0:
    print(f"\n{len(nan_points)} gap(s) detected:")
    for i, (idx, row) in enumerate(nan_points.iterrows(), 1):
        print(f"  Gap #{i} at: {row['record_datetime']}")

print("\n[OK] The line graph will break at these gaps, preventing misleading interpolation.")
print("="*80)

plt.show()
