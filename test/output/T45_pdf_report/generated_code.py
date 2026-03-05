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
import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic customer dataset
n_rows = 300

# Generate features
customer_id = np.arange(1, n_rows + 1)
age = np.random.randint(18, 70, n_rows)
income = np.random.normal(55000, 20000, n_rows).clip(20000, 150000)
tenure_months = np.random.randint(1, 72, n_rows)
spending_score = np.random.randint(1, 100, n_rows)

# Generate churn with some relationship to other variables
churn_prob = (
    0.3 * (tenure_months < 12) +
    0.2 * (spending_score < 30) +
    0.1 * (age > 55) +
    0.1 * (income < 30000)
)
churn_flag = (np.random.random(n_rows) < churn_prob).astype(int)

# Create DataFrame
df = pd.DataFrame({
    'customer_id': customer_id,
    'age': age,
    'income': income,
    'spending_score': spending_score,
    'tenure_months': tenure_months,
    'churn_flag': churn_flag
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

# Save dataset to CSV
df.to_csv('customer_data.csv', index=False)

# Create multi-page PDF report
with PdfPages('data_analysis_report.pdf') as pdf:
    # Page 1: Title page with summary statistics
    fig1 = plt.figure(figsize=(8.5, 11))
    fig1.suptitle('Customer Data Analysis Report', fontsize=16, fontweight='bold')
    
    # Add date and summary
    plt.text(0.5, 0.85, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
             ha='center', fontsize=12)
    plt.text(0.5, 0.75, f"Total Records: {len(df)}", ha='center', fontsize=12)
    plt.text(0.5, 0.70, f"Churn Rate: {df['churn_flag'].mean():.2%}", ha='center', fontsize=12)
    
    # Summary statistics table
    summary_stats = df.describe().round(2)
    table = plt.table(cellText=summary_stats.values,
                      rowLabels=summary_stats.index,
                      colLabels=summary_stats.columns,
                      loc='center',
                      bbox=[0.1, 0.1, 0.8, 0.5])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)
    
    plt.axis('off')
    pdf.savefig(fig1)
    plt.close(fig1)
    
    # Page 2: Side-by-side bar chart and line chart
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Bar chart: Average income by age group
    age_groups = pd.cut(df['age'], bins=[17, 25, 35, 45, 55, 65, 100], 
                        labels=['18-25', '26-35', '36-45', '46-55', '56-65', '65+'])
    income_by_age = df.groupby(age_groups)['income'].mean()
    ax1.bar(income_by_age.index, income_by_age.values, color='steelblue')
    ax1.set_title('Average Income by Age Group')
    ax1.set_xlabel('Age Group')
    ax1.set_ylabel('Average Income ($)')
    ax1.tick_params(axis='x', rotation=45)
    
    # Line chart: Average spending over tenure
    tenure_groups = pd.cut(df['tenure_months'], bins=[0, 12, 24, 36, 48, 60, 72], 
                           labels=['0-12', '13-24', '25-36', '37-48', '49-60', '60+'])
    spending_by_tenure = df.groupby(tenure_groups)['spending_score'].mean()
    ax2.plot(spending_by_tenure.index, spending_by_tenure.values, 
             marker='o', linewidth=2, markersize=8, color='darkorange')
    ax2.set_title('Average Spending Score by Tenure')
    ax2.set_xlabel('Tenure (months)')
    ax2.set_ylabel('Average Spending Score')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    pdf.savefig(fig2)
    plt.close(fig2)
    
    # Page 3: Heatmap of correlations
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    numeric_cols = ['age', 'income', 'spending_score', 'tenure_months', 'churn_flag']
    corr_matrix = df[numeric_cols].corr()
    
    im = ax3.imshow(corr_matrix, cmap='coolwarm', aspect='auto')
    plt.colorbar(im, ax=ax3)
    
    # Add correlation values
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            ax3.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}', 
                     ha='center', va='center', color='black', fontsize=10)
    
    ax3.set_xticks(np.arange(len(corr_matrix)))
    ax3.set_yticks(np.arange(len(corr_matrix)))
    ax3.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
    ax3.set_yticklabels(corr_matrix.columns)
    ax3.set_title('Correlation Heatmap')
    
    plt.tight_layout()
    pdf.savefig(fig3)
    plt.close(fig3)
    
    # Page 4: 2x2 grid of scatter plots
    fig4, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Scatter plot 1: income vs spending_score
    axes[0, 0].scatter(df['income'], df['spending_score'], alpha=0.6, c=df['churn_flag'], 
                       cmap='coolwarm', edgecolors='none')
    axes[0, 0].set_title('Income vs Spending Score')
    axes[0, 0].set_xlabel('Income ($)')
    axes[0, 0].set_ylabel('Spending Score')
    
    # Scatter plot 2: age vs tenure_months
    axes[0, 1].scatter(df['age'], df['tenure_months'], alpha=0.6, c=df['churn_flag'], 
                       cmap='coolwarm', edgecolors='none')
    axes[0, 1].set_title('Age vs Tenure')
    axes[0, 1].set_xlabel('Age')
    axes[0, 1].set_ylabel('Tenure (months)')
    
    # Scatter plot 3: age vs income
    axes[1, 0].scatter(df['age'], df['income'], alpha=0.6, c=df['churn_flag'], 
                       cmap='coolwarm', edgecolors='none')
    axes[1, 0].set_title('Age vs Income')
    axes[1, 0].set_xlabel('Age')
    axes[1, 0].set_ylabel('Income ($)')
    
    # Scatter plot 4: tenure_months vs spending_score
    axes[1, 1].scatter(df['tenure_months'], df['spending_score'], alpha=0.6, 
                       c=df['churn_flag'], cmap='coolwarm', edgecolors='none')
    axes[1, 1].set_title('Tenure vs Spending Score')
    axes[1, 1].set_xlabel('Tenure (months)')
    axes[1, 1].set_ylabel('Spending Score')
    
    plt.tight_layout()
    pdf.savefig(fig4)
    plt.close(fig4)
    
    # Page 5: Summary metrics table
    fig5 = plt.figure(figsize=(8.5, 11))
    fig5.suptitle('Summary Metrics', fontsize=16, fontweight='bold')
    
    # Create summary metrics for key variables
    metrics = ['mean', 'std', 'min', 'max']
    summary_data = []
    
    for col in ['age', 'income', 'spending_score', 'tenure_months', 'churn_flag']:
        row = [
            col,
            df[col].mean(),
            df[col].std(),
            df[col].min(),
            df[col].max()
        ]
        summary_data.append(row)
    
    summary_df = pd.DataFrame(summary_data, columns=['Variable', 'Mean', 'Std', 'Min', 'Max'])
    
    # Add churn rate separately
    churn_row = ['churn_rate', df['churn_flag'].mean(), df['churn_flag'].std(), 
                 df['churn_flag'].min(), df['churn_flag'].max()]
    summary_df.loc[len(summary_df)] = churn_row
    
    # Format table
    table = plt.table(cellText=summary_df.values,
                      colLabels=summary_df.columns,
                      loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.1, 1.1)
    
    plt.axis('off')
    pdf.savefig(fig5)
    plt.close(fig5)

print("Report saved as 'data_analysis_report.pdf'")