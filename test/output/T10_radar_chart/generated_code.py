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

# Sample data for 3 products across 7 attributes
attributes = ['Quality', 'Price', 'Design', 'Support', 'Speed', 'Reliability', 'Innovation']
products = {
    'Product A': [8, 6, 7, 9, 5, 8, 6],
    'Product B': [7, 8, 9, 6, 7, 7, 9],
    'Product C': [6, 9, 5, 8, 8, 6, 7]
}

# Number of variables
num_vars = len(attributes)

# Compute angle for each axis
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]  # Close the loop

# Create figure and axis
fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))

# Define colors for each product
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

# Plot each product
for idx, (product, values) in enumerate(products.items()):
    # Close the loop for values
    values += values[:1]
    
    # Draw the polygon
    ax.plot(angles, values, linewidth=2, linestyle='solid', label=product, color=colors[idx])
    ax.fill(angles, values, alpha=0.3, color=colors[idx])

# Add labels for each attribute
ax.set_xticks(angles[:-1])
ax.set_xticklabels(attributes, fontsize=12)

# Set y-axis limits
ax.set_ylim(0, 10)

# Add legend
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

# Add title
plt.title('Product Comparison Radar Chart', size=16, pad=20)

# Save the chart
plt.savefig('radar_chart.png', dpi=150, bbox_inches='tight')
plt.close()

print("Radar chart saved as 'radar_chart.png'")
print("Products compared: Product A, Product B, Product C")
print("Attributes:", attributes)