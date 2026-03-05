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
import matplotlib.pyplot as plt

# Load the dataset (assuming it's named 'dataset.csv' in the current directory)
df = pd.read_csv('dataset.csv')

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)

# Check for required columns (case-insensitive check)
lowercase_columns = {col.lower().strip(): col for col in df.columns}
if 'price' not in lowercase_columns or 'transmission' not in lowercase_columns:
    raise ValueError("Required columns 'price' and/or 'transmission' not found in dataset")

# Get original column names
price_col = lowercase_columns['price']
transmission_col = lowercase_columns['transmission']

# Create box plot of price grouped by transmission type
plt.figure(figsize=(10, 6))
df.boxplot(column=price_col, by=transmission_col)
plt.title('Price Distribution by Transmission Type')
plt.suptitle('')  # Remove default title that appears with boxplot
plt.xlabel('Transmission Type')
plt.ylabel('Price')
plt.tight_layout()
plt.savefig('price_by_transmission_boxplot.png', dpi=150, bbox_inches='tight')
plt.close()

print("Box plot saved as 'price_by_transmission_boxplot.png'")