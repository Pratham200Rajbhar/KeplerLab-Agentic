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

# Sample market share data for 6 companies
companies = ['Company A', 'Company B', 'Company C', 'Company D', 'Company E', 'Company F']
market_shares = [30, 20, 15, 12, 10, 13]

# Print dataset summary
print(f"Dataset: {len(companies)} companies")
print(f"Market shares: {market_shares}")
print(f"Total market share: {sum(market_shares)}%")

# Create figure with two subplots side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

# Colors for consistency
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6']

# Pie chart (left)
# Explode the largest slice (Company A with 30%)
explode = [0.1 if i == 0 else 0 for i in range(len(market_shares))]

wedges, texts, autotexts = ax1.pie(
    market_shares,
    labels=companies,
    autopct='%1.1f%%',
    startangle=90,
    colors=colors,
    explode=explode,
    shadow=True
)
ax1.set_title('Market Share - Pie Chart', fontsize=14, fontweight='bold')
ax1.axis('equal')  # Equal aspect ratio ensures pie is drawn as circle

# Donut chart (right)
# Create donut by adding a white circle in the center
wedges, texts, autotexts = ax2.pie(
    market_shares,
    labels=companies,
    autopct='%1.1f%%',
    startangle=90,
    colors=colors,
    wedgeprops=dict(width=0.3),  # Creates the donut hole
    shadow=True
)
ax2.set_title('Market Share - Donut Chart', fontsize=14, fontweight='bold')
ax2.axis('equal')  # Equal aspect ratio ensures donut is drawn as circle

# Add total percentage label in center of donut chart
ax2.text(0, 0, f'Total:\n{sum(market_shares)}%', 
         ha='center', va='center', fontsize=12, fontweight='bold')

# Adjust layout to prevent overlap
plt.tight_layout()

# Save the figure
plt.savefig('pie_donut_charts.png', dpi=150, bbox_inches='tight')
plt.close()

print("Charts saved as 'pie_donut_charts.png'")