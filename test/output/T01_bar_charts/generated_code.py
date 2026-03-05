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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Set professional style
plt.style.use('seaborn-v0_8-darkgrid')

# Create sample data for Q1-Q4 sales by product
products = ['Product A', 'Product B', 'Product C']
q1_sales = [120, 95, 140]
q2_sales = [135, 110, 155]
q3_sales = [145, 125, 165]
q4_sales = [160, 140, 180]

# Create DataFrame for grouped bar chart
sales_data = pd.DataFrame({
    'Product': products,
    'Q1': q1_sales,
    'Q2': q2_sales,
    'Q3': q3_sales,
    'Q4': q4_sales
})

print("Sales Data Summary:")
print(f"Dataset: {sales_data.shape[0]} rows, {sales_data.shape[1]} columns")
print("Columns:", list(sales_data.columns))
print(sales_data)

# Create grouped bar chart
fig, ax = plt.subplots(figsize=(10, 6))

# Set positions for grouped bars
x = np.arange(len(products))  # the label locations
width = 0.2  # the width of the bars

# Plot each quarter
ax.bar(x - 1.5*width, q1_sales, width, label='Q1', color='#2ecc71')
ax.bar(x - 0.5*width, q2_sales, width, label='Q2', color='#3498db')
ax.bar(x + 0.5*width, q3_sales, width, label='Q3', color='#9b59b6')
ax.bar(x + 1.5*width, q4_sales, width, label='Q4', color='#e74c3c')

# Add labels, title, and formatting
ax.set_xlabel('Products', fontsize=12)
ax.set_ylabel('Sales (in thousands)', fontsize=12)
ax.set_title('Quarterly Sales Comparison by Product (Q1-Q4)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(products)
ax.legend(title='Quarter', loc='upper left')

# Add grid and value annotations
ax.grid(True, axis='y', alpha=0.7)
for i, (q1, q2, q3, q4) in enumerate(zip(q1_sales, q2_sales, q3_sales, q4_sales)):
    ax.text(i - 1.5*width, q1 + 3, str(q1), ha='center', va='bottom', fontsize=9)
    ax.text(i - 0.5*width, q2 + 3, str(q2), ha='center', va='bottom', fontsize=9)
    ax.text(i + 0.5*width, q3 + 3, str(q3), ha='center', va='bottom', fontsize=9)
    ax.text(i + 1.5*width, q4 + 3, str(q4), ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('bar_grouped.png', dpi=150, bbox_inches='tight')
plt.close()

# Create market share data for stacked bar chart
regions = ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East']
product_a_share = [35, 30, 45, 25, 20]
product_b_share = [30, 35, 25, 35, 30]
product_c_share = [35, 35, 30, 40, 50]

# Create DataFrame for stacked chart
market_data = pd.DataFrame({
    'Region': regions,
    'Product A': product_a_share,
    'Product B': product_b_share,
    'Product C': product_c_share
})

print("\nMarket Share Data Summary:")
print(f"Dataset: {market_data.shape[0]} rows, {market_data.shape[1]} columns")
print("Columns:", list(market_data.columns))
print(market_data)

# Create stacked bar chart
fig, ax = plt.subplots(figsize=(10, 6))

# Plot stacked bars
ax.bar(regions, product_a_share, label='Product A', color='#2ecc71')
ax.bar(regions, product_b_share, bottom=product_a_share, label='Product B', color='#3498db')
ax.bar(regions, product_c_share, bottom=np.array(product_a_share) + np.array(product_b_share), 
       label='Product C', color='#9b59b6')

# Add labels, title, and formatting
ax.set_xlabel('Regions', fontsize=12)
ax.set_ylabel('Market Share (%)', fontsize=12)
ax.set_title('Market Share by Product Across Regions', fontsize=14, fontweight='bold')
ax.set_ylim(0, 100)
ax.legend(title='Products', loc='upper right')

# Add percentage labels on segments
for i, (a, b, c) in enumerate(zip(product_a_share, product_b_share, product_c_share)):
    total = a + b + c
    ax.text(i, a/2, f'{a}%', ha='center', va='center', fontsize=9, color='white')
    ax.text(i, a + b/2, f'{b}%', ha='center', va='center', fontsize=9, color='white')
    ax.text(i, a + b + c/2, f'{c}%', ha='center', va='center', fontsize=9, color='white')

plt.tight_layout()
plt.savefig('bar_stacked.png', dpi=150, bbox_inches='tight')
plt.close()