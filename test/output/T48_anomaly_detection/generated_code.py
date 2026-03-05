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
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
import joblib

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic sensor data (500 rows, 3 features)
n_samples = 500
n_anomalies = int(n_samples * 0.05)  # ~5% anomalies = 25 anomalies

# Generate normal data from multivariate normal distribution
mean = [10, 20, 15]
cov = [[5, 2, 1], [2, 8, 3], [1, 3, 6]]
X_normal = np.random.multivariate_normal(mean, cov, n_samples - n_anomalies)

# Generate anomalies (using different distributions to ensure they stand out)
# Method 1: Random points far from the main cluster
X_anomalies_1 = np.random.uniform(low=[25, 35, 25], high=[35, 50, 35], size=(n_anomalies//2, 3))
# Method 2: Points with very low values
X_anomalies_2 = np.random.uniform(low=[-10, -5, -10], high=[0, 5, 0], size=(n_anomalies - n_anomalies//2, 3))

# Combine normal and anomaly data
X = np.vstack([X_normal, X_anomalies_1, X_anomalies_2])
y_true = np.array([0] * (n_samples - n_anomalies) + [1] * n_anomalies)  # 0 = normal, 1 = anomaly

# Create DataFrame
df = pd.DataFrame(X, columns=['sensor_temp', 'sensor_pressure', 'sensor_vibration'])
df['true_anomaly'] = y_true

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("Data types:", df.dtypes)
print("\nMissing values:", df.isnull().sum().sum())
print("\nDescriptive statistics:")
print(df.describe())

# Standardize the data for anomaly detection algorithms
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[['sensor_temp', 'sensor_pressure', 'sensor_vibration']])

# Apply Isolation Forest
iso_forest = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
iso_forest.fit(X_scaled)
iso_pred = iso_forest.predict(X_scaled)  # -1 for anomalies, 1 for normal
iso_scores = -iso_forest.score_samples(X_scaled)  # Higher score = more anomalous

# Apply Local Outlier Factor
lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05, novelty=True)
lof.fit(X_scaled)
lof_pred = lof.predict(X_scaled)  # -1 for anomalies, 1 for normal
lof_scores = -lof.score_samples(X_scaled)  # Higher score = more anomalous

# Convert predictions to binary (1 = anomaly, 0 = normal)
iso_anomalies = (iso_pred == -1).astype(int)
lof_anomalies = (lof_pred == -1).astype(int)

# Create predictions DataFrame
predictions_df = df.copy()
predictions_df['iso_forest_anomaly'] = iso_anomalies
predictions_df['lof_anomaly'] = lof_anomalies
predictions_df['iso_score'] = iso_scores
predictions_df['lof_score'] = lof_scores

# Save predictions to CSV
predictions_df.to_csv('anomaly_predictions.csv', index=False)

# Print key results
print(f"\nIsolation Forest detected {iso_anomalies.sum()} anomalies")
print(f"LOF detected {lof_anomalies.sum()} anomalies")
print(f"True anomalies: {y_true.sum()}")

# Calculate agreement metrics
agreement = (iso_anomalies == lof_anomalies).sum()
print(f"\nAgreement between methods: {agreement}/{n_samples} ({100*agreement/n_samples:.1f}%)")

# Create visualizations
# 1. Scatter plots colored by anomaly status for each method
# Use first two features for scatter plots
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Isolation Forest scatter plot
scatter1 = axes[0].scatter(
    df['sensor_temp'], df['sensor_pressure'],
    c=iso_anomalies, cmap='coolwarm', alpha=0.7, s=50, edgecolors='k', linewidth=0.5
)
axes[0].set_xlabel('sensor_temp')
axes[0].set_ylabel('sensor_pressure')
axes[0].set_title('Isolation Forest Anomaly Detection')
axes[0].legend(*scatter1.legend_elements(), title="Anomaly", loc='upper right')

# LOF scatter plot
scatter2 = axes[1].scatter(
    df['sensor_temp'], df['sensor_pressure'],
    c=lof_anomalies, cmap='coolwarm', alpha=0.7, s=50, edgecolors='k', linewidth=0.5
)
axes[1].set_xlabel('sensor_temp')
axes[1].set_ylabel('sensor_pressure')
axes[1].set_title('LOF Anomaly Detection')
axes[1].legend(*scatter2.legend_elements(), title="Anomaly", loc='upper right')

plt.tight_layout()
plt.savefig('anomaly_scatter_plots.png', dpi=150, bbox_inches='tight')
plt.close()

# 2. Anomaly score distributions
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Isolation Forest score distribution
axes[0].hist(iso_scores, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
axes[0].axvline(x=np.percentile(iso_scores, 95), color='red', linestyle='--', label='95th percentile')
axes[0].set_xlabel('Anomaly Score')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Isolation Forest Anomaly Score Distribution')
axes[0].legend()

# LOF score distribution
axes[1].hist(lof_scores, bins=30, color='darkorange', alpha=0.7, edgecolor='black')
axes[1].axvline(x=np.percentile(lof_scores, 95), color='red', linestyle='--', label='95th percentile')
axes[1].set_xlabel('Anomaly Score')
axes[1].set_ylabel('Frequency')
axes[1].set_title('LOF Anomaly Score Distribution')
axes[1].legend()

plt.tight_layout()
plt.savefig('anomaly_score_distributions.png', dpi=150, bbox_inches='tight')
plt.close()

# 3. Agreement heatmap between methods
# Create confusion matrix for agreement
cm = confusion_matrix(iso_anomalies, lof_anomalies)
cm_df = pd.DataFrame(cm, index=['Isolation_Forest_0', 'Isolation_Forest_1'],
                     columns=['LOF_0', 'LOF_1'])

plt.figure(figsize=(8, 6))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues', cbar_kws={'label': 'Count'})
plt.title('Agreement Between Isolation Forest and LOF')
plt.xlabel('LOF Prediction')
plt.ylabel('Isolation Forest Prediction')
plt.tight_layout()
plt.savefig('agreement_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()

# Save the trained models
joblib.dump(iso_forest, 'isolation_forest_model.pkl')
joblib.dump(lof, 'lof_model.pkl')

print("\nFiles saved:")
print("- anomaly_predictions.csv")
print("- anomaly_scatter_plots.png")
print("- anomaly_score_distributions.png")
print("- agreement_heatmap.png")
print("- isolation_forest_model.pkl")
print("- lof_model.pkl")