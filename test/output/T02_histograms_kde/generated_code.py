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
from scipy import stats

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic data for 500 samples
n_samples = 500
data = {
    'height': np.random.normal(loc=170, scale=10, size=n_samples),  # cm
    'weight': np.random.normal(loc=70, scale=15, size=n_samples),    # kg
    'age': np.random.normal(loc=35, scale=12, size=n_samples),       # years
    'income': np.random.normal(loc=50000, scale=15000, size=n_samples)  # dollars
}

# Create DataFrame
df = pd.DataFrame(data)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nDescriptive Statistics:")
print(df.describe())

# Create 2x2 subplot figure
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

# Define features and their titles
features = ['height', 'weight', 'age', 'income']
titles = ['Height (cm)', 'Weight (kg)', 'Age (years)', 'Income ($)']

# Plot histograms with KDE for each feature
for i, (feature, title) in enumerate(zip(features, titles)):
    # Get data
    values = df[feature]
    
    # Calculate mean and std
    mean_val = values.mean()
    std_val = values.std()
    
    # Plot histogram
    axes[i].hist(values, bins=30, density=True, alpha=0.7, color='skyblue', edgecolor='black')
    
    # Plot KDE
    x_min, x_max = values.min(), values.max()
    x = np.linspace(x_min, x_max, 100)
    kde = stats.gaussian_kde(values)
    axes[i].plot(x, kde(x), 'r-', linewidth=2, label='KDE')
    
    # Add mean and std annotations
    textstr = f'Mean: {mean_val:.2f}\nStd: {std_val:.2f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    axes[i].text(0.05, 0.95, textstr, transform=axes[i].transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    # Set labels and title
    axes[i].set_xlabel(feature.capitalize())
    axes[i].set_ylabel('Density')
    axes[i].set_title(title)
    axes[i].legend(loc='upper right')

# Adjust layout
plt.tight_layout()

# Save the figure
plt.savefig('histograms_kde.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nFigure saved as 'histograms_kde.png'")