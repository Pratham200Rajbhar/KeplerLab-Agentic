import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as _plt_module
_original_show = _plt_module.show

def _capture_show():
    import io, base64
    buf = io.BytesIO()
    _plt_module.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    print(f"__CHART__:{encoded}")
    _plt_module.close('all')

_plt_module.show = _capture_show

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic time-series data for 4 products over 24 months
months = pd.date_range(start='2022-01-01', periods=24, freq='M')
products = ['Product A', 'Product B', 'Product C', 'Product D']

# Create revenue data with realistic ranges and some trend/seasonality
data = {}
for i, product in enumerate(products):
    # Base revenue with trend and seasonal component
    base = 50000 + i * 15000  # Different base revenues for each product
    trend = np.linspace(0, 20000, 24)  # Upward trend
    seasonal = 10000 * np.sin(2 * np.pi * np.arange(24) / 12)  # Seasonal pattern
    noise = np.random.normal(0, 5000, 24)  # Random noise
    
    # Combine components and ensure positive values
    revenue = base + trend + seasonal + noise
    revenue = np.maximum(revenue, 1000)  # Ensure minimum revenue
    
    data[product] = revenue

# Create DataFrame
df = pd.DataFrame(data, index=months)
df.index.name = 'Month'
df = df.round(2)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nDescriptive statistics:")
print(df.describe())

# Save the synthetic data to CSV
df.to_csv('synthetic_revenue_data.csv')

# Create multi-line chart with markers
plt.figure(figsize=(12, 6))
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

for i, product in enumerate(products):
    plt.plot(df.index, df[product], marker='o', linewidth=2, markersize=6, 
             label=product, color=colors[i])

plt.title('Monthly Revenue by Product (24 Months)', fontsize=16)
plt.xlabel('Month', fontsize=12)
plt.ylabel('Revenue ($)', fontsize=12)
plt.legend(loc='upper left', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(rotation=45)
plt.tight_layout()

# Save the line chart
plt.savefig('line_chart.png', dpi=150, bbox_inches='tight')
plt.close()

# Create stacked area chart
plt.figure(figsize=(12, 6))

# Create stacked area chart
plt.stackplot(df.index, *[df[product] for product in products], 
              labels=products, colors=colors, alpha=0.8)

plt.title('Stacked Revenue by Product (24 Months)', fontsize=16)
plt.xlabel('Month', fontsize=12)
plt.ylabel('Revenue ($)', fontsize=12)
plt.legend(loc='upper left', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(rotation=45)
plt.tight_layout()

# Save the area chart
plt.savefig('area_chart.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nCharts saved as 'line_chart.png' and 'area_chart.png'")
print("Synthetic data saved as 'synthetic_revenue_data.csv'")