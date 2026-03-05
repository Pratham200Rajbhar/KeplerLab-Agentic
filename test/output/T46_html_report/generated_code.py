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

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import random
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Generate synthetic e-commerce dataset with 200 rows
n_rows = 200
categories = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books']
dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(200)]

# Create data
data = {
    'order_id': [f'ORD{str(i).zfill(5)}' for i in range(1, n_rows + 1)],
    'date': dates,
    'category': np.random.choice(categories, n_rows),
    'revenue': np.round(np.random.uniform(10, 500, n_rows), 2),
    'quantity': np.random.randint(1, 10, n_rows),
    'customer_id': [f'CUST{str(np.random.randint(1, 100)).zfill(3)}' for _ in range(n_rows)]
}

# Create DataFrame
df = pd.DataFrame(data)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)

# Handle missing values (none in this synthetic dataset, but check anyway)
print("\nMissing values:")
print(df.isnull().sum())

# Generate descriptive statistics
print("\nDescriptive Statistics:")
print(df.describe())

# Create visualizations
# 1. Bar chart: Revenue by category
plt.figure(figsize=(10, 6))
category_revenue = df.groupby('category')['revenue'].sum().sort_values(ascending=False)
plt.bar(category_revenue.index, category_revenue.values, color='steelblue')
plt.title('Total Revenue by Category')
plt.xlabel('Category')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('revenue_by_category.png', dpi=150, bbox_inches='tight')
plt.close()

# 2. Line chart: Daily revenue trend
plt.figure(figsize=(12, 6))
daily_revenue = df.groupby('date')['revenue'].sum()
plt.plot(daily_revenue.index, daily_revenue.values, color='darkgreen', linewidth=2)
plt.title('Daily Revenue Trend')
plt.xlabel('Date')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('daily_revenue_trend.png', dpi=150, bbox_inches='tight')
plt.close()

# 3. Scatter plot: Revenue vs Quantity
plt.figure(figsize=(10, 6))
plt.scatter(df['quantity'], df['revenue'], alpha=0.7, c='purple')
plt.title('Revenue vs Quantity')
plt.xlabel('Quantity')
plt.ylabel('Revenue ($)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('revenue_vs_quantity.png', dpi=150, bbox_inches='tight')
plt.close()

# Convert charts to base64
def image_to_base64(filepath):
    with open(filepath, 'rb') as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

revenue_by_category_b64 = image_to_base64('revenue_by_category.png')
daily_revenue_b64 = image_to_base64('daily_revenue_trend.png')
revenue_vs_quantity_b64 = image_to_base64('revenue_vs_quantity.png')

# Prepare data for HTML table (first 20 rows for readability)
html_table_data = df.head(20).to_html(index=False, classes='data-table')

# Generate key insights
insights = [
    f"Total orders analyzed: {df.shape[0]}",
    f"Revenue range: ${df['revenue'].min():.2f} - ${df['revenue'].max():.2f}",
    f"Average revenue per order: ${df['revenue'].mean():.2f}",
    f"Most popular category: {df['category'].mode()[0]}",
    f"Total revenue: ${df['revenue'].sum():.2f}",
    f"Average quantity per order: {df['quantity'].mean():.1f} units"
]

# Create HTML report
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-commerce Data Analysis Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 5px solid #3498db;
            padding-left: 10px;
        }}
        .summary {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .summary-table th, .summary-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .summary-table th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}
        .summary-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .insights {{
            background-color: #e8f4f8;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        .insights ul {{
            padding-left: 20px;
        }}
        .insights li {{
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        .chart-container {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }}
        .data-table th, .data-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .data-table th {{
            background-color: #2c3e50;
            color: white;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        .data-table th:hover {{
            background-color: #34495e;
        }}
        .data-table th::after {{
            content: '↕';
            position: absolute;
            right: 10px;
            font-size: 10px;
            opacity: 0.5;
        }}
        .data-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .data-table tr:hover {{
            background-color: #e8f4f8;
        }}
        .data-table-container {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
            margin-bottom: 30px;
        }}
        .footer {{
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>E-commerce Data Analysis Report</h1>
        
        <div class="summary">
            <h2>Dataset Summary</h2>
            <p><strong>Total Records:</strong> {df.shape[0]} orders</p>
            <p><strong>Columns:</strong> {', '.join(df.columns)}</p>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Statistic</th>
                        <th>Revenue ($)</th>
                        <th>Quantity</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Mean</td>
                        <td>{df['revenue'].mean():.2f}</td>
                        <td>{df['quantity'].mean():.1f}</td>
                    </tr>
                    <tr>
                        <td>Median</td>
                        <td>{df['revenue'].median():.2f}</td>
                        <td>{df['quantity'].median():.1f}</td>
                    </tr>
                    <tr>
                        <td>Std Dev</td>
                        <td>{df['revenue'].std():.2f}</td>
                        <td>{df['quantity'].std():.1f}</td>
                    </tr>
                    <tr>
                        <td>Min</td>
                        <td>{df['revenue'].min():.2f}</td>
                        <td>{df['quantity'].min()}</td>
                    </tr>
                    <tr>
                        <td>Max</td>
                        <td>{df['revenue'].max():.2f}</td>
                        <td>{df['quantity'].max()}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="insights">
            <h2>Key Insights</h2>
            <ul>
                <li>{insights[0]}</li>
                <li>{insights[1]}</li>
                <li>{insights[2]}</li>
                <li>{insights[3]}</li>
                <li>{insights[4]}</li>
                <li>{insights[5]}</li>
            </ul>
        </div>
        
        <div class="chart-container">
            <h2>Revenue by Category</h2>
            <img src="data:image/png;base64,{revenue_by_category_b64}" alt="Revenue by Category">
        </div>
        
        <div class="chart-container">
            <h2>Daily Revenue Trend</h2>
            <img src="data:image/png;base64,{daily_revenue_b64}" alt="Daily Revenue Trend">
        </div>
        
        <div class="chart-container">
            <h2>Revenue vs Quantity</h2>
            <img src="data:image/png;base64,{revenue_vs_quantity_b64}" alt="Revenue vs Quantity">
        </div>
        
        <div class="data-table-container">
            <h2>Sample Data (First 20 Orders)</h2>
            {df.head(20).to_html(index=False, classes='data-table')}
        </div>
        
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | E-commerce Data Analysis Report</p>
        </div>
    </div>
    
    <script>
        // Sortable table functionality
        document.addEventListener('DOMContentLoaded', function() {{
            const table = document.querySelector('.data-table');
            const headers = table.querySelectorAll('th');
            
            headers.forEach((header, index) => {{
                header.addEventListener('click', function() {{
                    const table = this.parentElement.parentElement.parentElement;
                    const body = table.querySelector('tbody');
                    const rows = Array.from(body.querySelectorAll('tr'));
                    const sortedRows = rows.sort((a, b) => {{
                        const aVal = a.querySelectorAll('td')[index].textContent;
                        const bVal = b.querySelectorAll('td')[index].textContent;
                        
                        // Try numeric comparison first
                        const aNum = parseFloat(aVal.replace(/[^0-9.-]+/g, ''));
                        const bNum = parseFloat(bVal.replace(/[^0-9.-]+/g, ''));
                        
                        if (!isNaN(aNum) && !isNaN(bNum)) {{
                            return aNum - bNum;
                        }}
                        
                        // String comparison
                        return aVal.localeCompare(bVal);
                    }});
                    
                    // Toggle sort direction
                    const isAscending = this.getAttribute('data-sort') === 'asc';
                    if (!isAscending) {{
                        sortedRows.reverse();
                    }}
                    
                    // Update sort indicator
                    headers.forEach(h => h.removeAttribute('data-sort'));
                    this.setAttribute('data-sort', isAscending ? 'desc' : 'asc');
                    
                    // Rebuild table
                    sortedRows.forEach(row => body.appendChild(row));
                }});
            }});
        }});
    </script>
</body>
</html>"""

# Save HTML report
with open('analysis_report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("\nAnalysis complete!")
print("Files created:")
print("- revenue_by_category.png")
print("- daily_revenue_trend.png")
print("- revenue_vs_quantity.png")
print("- analysis_report.html")