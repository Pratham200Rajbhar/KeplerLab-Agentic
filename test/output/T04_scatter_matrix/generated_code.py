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
from sklearn.datasets import make_blobs

# Generate synthetic dataset with 4 features and 3 classes
X, y = make_blobs(n_samples=300, centers=3, n_features=4, random_state=42, cluster_std=0.8)

# Create DataFrame with feature names
df = pd.DataFrame(X, columns=['sepal_length', 'sepal_width', 'petal_length', 'petal_width'])
df['class'] = y

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())
print("\nDescriptive statistics:")
print(df.describe())

# Create pair plot with scatter matrix
g = sns.pairplot(df, vars=['sepal_length', 'sepal_width', 'petal_length', 'petal_width'], 
                 hue='class', diag_kind='kde', corner=False, plot_kws={'alpha': 0.7})

# Add correlation coefficients in upper triangle
for i, row_var in enumerate(['sepal_length', 'sepal_width', 'petal_length', 'petal_width']):
    for j, col_var in enumerate(['sepal_length', 'sepal_width', 'petal_length', 'petal_width']):
        if i < j:  # upper triangle
            ax = g.axes[i, j]
            corr = df[row_var].corr(df[col_var])
            ax.text(0.5, 0.5, f'r = {corr:.2f}', transform=ax.transAxes, 
                    ha='center', va='center', fontsize=12, fontweight='bold')

# Save figure
plt.savefig('scatter_matrix.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved scatter_matrix.png')

# Save dataset to CSV
df.to_csv('synthetic_dataset.csv', index=False)
print('Saved synthetic_dataset.csv')