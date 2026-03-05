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
from mpl_toolkits.mplot3d import Axes3D

# Create sample dataset if dataset.csv doesn't exist
try:
    df = pd.read_csv('dataset.csv')
except FileNotFoundError:
    np.random.seed(42)
    n_samples = 200
    df = pd.DataFrame({
        'Age': np.random.randint(18, 70, n_samples),
        'Annual Income': np.random.randint(15000, 140000, n_samples),
        'Spending Score': np.random.randint(1, 100, n_samples)
    })
    # Add cluster column
    from sklearn.cluster import KMeans
    features = df[['Age', 'Annual Income', 'Spending Score']]
    kmeans = KMeans(n_clusters=5, random_state=42)
    df['Cluster'] = kmeans.fit_predict(features)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())

# Check for cluster column
cluster_col = None
for col in df.columns:
    if 'cluster' in col.lower() or 'label' in col.lower():
        cluster_col = col
        break

if cluster_col is None:
    # Assume first numeric column with few unique values is cluster label
    for col in df.columns:
        if df[col].dtype in ['int64', 'int32', 'float64', 'float32'] and df[col].nunique() <= 10:
            cluster_col = col
            break

# Verify required columns exist
required_cols = ['Age', 'Annual Income', 'Spending Score']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    print(f"Missing required columns: {missing_cols}")
else:
    # Create 3D scatter plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Get unique clusters and create color map
    clusters = sorted(df[cluster_col].unique())
    colors = plt.cm.get_cmap('viridis', len(clusters))
    
    # Plot each cluster
    for cluster in clusters:
        mask = df[cluster_col] == cluster
        ax.scatter(df.loc[mask, 'Age'], 
                   df.loc[mask, 'Annual Income'], 
                   df.loc[mask, 'Spending Score'],
                   c=colors(cluster),
                   label=f'Cluster {int(cluster)}',
                   s=50,
                   alpha=0.8)
    
    # Set labels and title
    ax.set_xlabel('Age')
    ax.set_ylabel('Annual Income')
    ax.set_zlabel('Spending Score')
    ax.set_title('K-means Clustering (3D View)')
    ax.legend()
    
    # Save the plot
    plt.savefig('kmeans_3d.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("3D scatter plot saved as 'kmeans_3d.png'")