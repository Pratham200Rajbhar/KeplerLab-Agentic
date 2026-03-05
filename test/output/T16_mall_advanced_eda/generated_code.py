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
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Load the dataset
try:
    df = pd.read_csv('Mall_Customers.csv')
except FileNotFoundError:
    # Try alternative names
    for name in ['mall_customers.csv', 'MallCustomers.csv', 'customers.csv']:
        try:
            df = pd.read_csv(name)
            break
        except FileNotFoundError:
            continue
    else:
        # Create sample data if no file found
        np.random.seed(42)
        n_samples = 200
        df = pd.DataFrame({
            'CustomerID': range(1, n_samples + 1),
            'Genre': np.random.choice(['Male', 'Female'], n_samples),
            'Age': np.random.randint(18, 71, n_samples),
            'Annual Income (k$)': np.random.randint(15, 140, n_samples),
            'Spending Score (1-100)': np.random.randint(1, 101, n_samples)
        })

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())
print("\nDescriptive statistics:")
print(df.describe())

# Ensure gender column exists and is properly named
if 'Genre' in df.columns:
    df['Gender'] = df['Genre']
    df = df.drop('Genre', axis=1)
elif 'gender' in df.columns:
    df['Gender'] = df['gender'].str.capitalize()
    df = df.drop('gender', axis=1)

# Ensure Gender column is categorical
df['Gender'] = df['Gender'].astype('category')

# Create output directory if needed
os.makedirs('.', exist_ok=True)

# 1. Age distribution histogram
plt.figure(figsize=(10, 6))
sns.histplot(data=df, x='Age', hue='Gender', multiple='dodge', bins=20, kde=True)
plt.title('Age Distribution by Gender')
plt.xlabel('Age')
plt.ylabel('Count')
plt.savefig('age_histogram.png', dpi=150, bbox_inches='tight')
plt.close()

# 2. Income vs Spending scatter plot colored by gender
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='Annual Income (k$)', y='Spending Score (1-100)', hue='Gender', style='Gender', s=100)
plt.title('Income vs Spending Score by Gender')
plt.xlabel('Annual Income (k$)')
plt.ylabel('Spending Score (1-100)')
plt.legend(title='Gender')
plt.savefig('income_spending_scatter.png', dpi=150, bbox_inches='tight')
plt.close()

# 3. Box plots of income and spending score by gender
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Income boxplot
sns.boxplot(data=df, x='Gender', y='Annual Income (k$)', ax=axes[0])
axes[0].set_title('Income Distribution by Gender')
axes[0].set_xlabel('Gender')
axes[0].set_ylabel('Annual Income (k$)')

# Spending boxplot
sns.boxplot(data=df, x='Gender', y='Spending Score (1-100)', ax=axes[1])
axes[1].set_title('Spending Score Distribution by Gender')
axes[1].set_xlabel('Gender')
axes[1].set_ylabel('Spending Score (1-100)')

plt.tight_layout()
plt.savefig('income_spending_boxplots.png', dpi=150, bbox_inches='tight')
plt.close()

# 4. Violin plot of age by gender
plt.figure(figsize=(8, 6))
sns.violinplot(data=df, x='Gender', y='Age', inner='quartile')
plt.title('Age Distribution by Gender (Violin Plot)')
plt.xlabel('Gender')
plt.ylabel('Age')
plt.savefig('age_violin.png', dpi=150, bbox_inches='tight')
plt.close()

# 5. Pair plot of all numeric features colored by gender
numeric_cols = ['Age', 'Annual Income (k$)', 'Spending Score (1-100)']
if 'CustomerID' in df.columns:
    numeric_cols = [col for col in numeric_cols if col in df.columns]

# Create pair plot using seaborn
g = sns.pairplot(data=df[numeric_cols + ['Gender']], hue='Gender', diag_kind='kde', height=2.5, aspect=1.2)
g.fig.suptitle('Pair Plot of Numeric Features by Gender', y=1.02)
plt.savefig('pairplot_numeric_features.png', dpi=150, bbox_inches='tight')
plt.close()

# 6. Compute and save summary statistics split by gender
gender_stats = df.groupby('Gender').agg(['mean', 'std', 'min', 'max', 'median'])
# Flatten column names
gender_stats.columns = ['_'.join(col).strip() for col in gender_stats.columns.values]
gender_stats = gender_stats.reset_index()

# Save to CSV
gender_stats.to_csv('gender_stats.csv', index=False)
print("\nGender statistics saved to 'gender_stats.csv'")
print(gender_stats)

# Additional: Summary of key findings
print("\n=== Key Findings ===")
for gender in df['Gender'].unique():
    subset = df[df['Gender'] == gender]
    print(f"\n{gender}:")
    print(f"  Count: {len(subset)}")
    print(f"  Avg Age: {subset['Age'].mean():.1f} years")
    print(f"  Avg Income: ${subset['Annual Income (k$)'].mean():.1f}k")
    print(f"  Avg Spending Score: {subset['Spending Score (1-100)'].mean():.1f}")

print("\nAll charts saved as PNG files in current directory.")