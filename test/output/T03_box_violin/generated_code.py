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

# Generate synthetic salary data for 5 departments
departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance']
n_samples_per_dept = 100

# Create salary data with department-specific characteristics
salaries = []
dept_labels = []

for dept in departments:
    if dept == 'Engineering':
        mean_salary = 95000
        std_salary = 15000
    elif dept == 'Marketing':
        mean_salary = 75000
        std_salary = 12000
    elif dept == 'Sales':
        mean_salary = 80000
        std_salary = 18000
    elif dept == 'HR':
        mean_salary = 65000
        std_salary = 10000
    else:  # Finance
        mean_salary = 85000
        std_salary = 14000
    
    dept_salaries = np.random.normal(loc=mean_salary, scale=std_salary, size=n_samples_per_dept)
    dept_salaries = np.clip(dept_salaries, 40000, 200000)  # Realistic salary bounds
    
    salaries.extend(dept_salaries)
    dept_labels.extend([dept] * n_samples_per_dept)

# Create DataFrame
df = pd.DataFrame({
    'Department': dept_labels,
    'Salary': salaries
})

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())
print("\nDescriptive statistics:")
print(df.groupby('Department')['Salary'].describe())

# Create side-by-side figure with box plots and violin plots
fig, axes = plt.subplots(1, 2, figsize=(14, 8))

# Box plots on the left
sns.boxplot(data=df, x='Department', y='Salary', ax=axes[0])
axes[0].set_title('Salary Distribution by Department (Box Plot)', fontsize=14)
axes[0].set_xlabel('Department', fontsize=12)
axes[0].set_ylabel('Salary ($)', fontsize=12)
axes[0].tick_params(axis='x', rotation=45)

# Violin plots with swarm overlay on the right
sns.violinplot(data=df, x='Department', y='Salary', ax=axes[1], inner=None, alpha=0.3)
sns.swarmplot(data=df, x='Department', y='Salary', ax=axes[1], size=3, color='black', alpha=0.7)
axes[1].set_title('Salary Distribution by Department (Violin + Swarm)', fontsize=14)
axes[1].set_xlabel('Department', fontsize=12)
axes[1].set_ylabel('Salary ($)', fontsize=12)
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('salary_distribution.png', dpi=150, bbox_inches='tight')
plt.close()

# Save the synthetic data to CSV
df.to_csv('synthetic_salary_data.csv', index=False)

print("\nFigure saved as 'salary_distribution.png'")
print("Data saved as 'synthetic_salary_data.csv'")