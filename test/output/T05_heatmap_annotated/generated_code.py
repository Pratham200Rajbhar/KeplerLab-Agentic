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
import seaborn as sns
import matplotlib.pyplot as plt

# Generate synthetic dataset with 10 features and 500 rows
np.random.seed(42)
data = np.random.randn(500, 10)
feature_names = [f'Feature_{i+1}' for i in range(10)]
df = pd.DataFrame(data, columns=feature_names)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)

# Compute Pearson correlation matrix
corr_matrix = df.corr(method='pearson')

# Create annotated heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0,
            square=True, cbar_kws={"shrink": .8}, linewidths=0.5)
plt.title('Pearson Correlation Heatmap (Annotated)')
plt.tight_layout()
plt.savefig('correlation_heatmap_annotated.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nCorrelation matrix saved as 'correlation_heatmap_annotated.png'")
print("\nCorrelation matrix (rounded to 2 decimal places):")
print(corr_matrix.round(2))