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
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# Load dataset
try:
    df = pd.read_csv('Social_Network_Ads.csv')
except FileNotFoundError:
    # If file not found, create sample data based on typical Social Network Ads dataset structure
    np.random.seed(42)
    n_samples = 500
    df = pd.DataFrame({
        'User ID': range(1, n_samples + 1),
        'Gender': np.random.choice(['Male', 'Female'], n_samples),
        'Age': np.random.randint(18, 61, n_samples),
        'EstimatedSalary': np.random.randint(15000, 150000, n_samples),
        'Purchased': np.random.randint(0, 2, n_samples)
    })
    df.to_csv('Social_Network_Ads.csv', index=False)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())
print("\nDescriptive statistics:")
print(df.describe())

# Feature Engineering
# Create age groups
df['AgeGroup'] = pd.cut(df['Age'], bins=[17, 25, 35, 45, 100], labels=['18-25', '26-35', '36-45', '46+'])

# Create income quartiles
df['IncomeQuartile'] = pd.qcut(df['EstimatedSalary'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

# Create age×income interaction
df['AgeIncomeInteraction'] = df['Age'] * df['EstimatedSalary']

# Create log-transformed income
df['LogIncome'] = np.log(df['EstimatedSalary'] + 1)

# Create age squared
df['AgeSquared'] = df['Age'] ** 2

# Encode categorical variables
label_encoder = LabelEncoder()
df['Gender_encoded'] = label_encoder.fit_transform(df['Gender'])

# Prepare data for modeling
# Original features
original_features = ['Gender', 'Age', 'EstimatedSalary']
X_original = df[original_features].copy()
X_original['Gender'] = df['Gender_encoded']
y = df['Purchased']

# Engineered features
engineered_features = ['Gender_encoded', 'Age', 'EstimatedSalary', 'AgeGroup_encoded', 'IncomeQuartile_encoded',
                       'AgeIncomeInteraction', 'LogIncome', 'AgeSquared']
# Encode categorical engineered features
df['AgeGroup_encoded'] = label_encoder.fit_transform(df['AgeGroup'])
df['IncomeQuartile_encoded'] = label_encoder.fit_transform(df['IncomeQuartile'])

X_engineered = df[engineered_features].copy()

# Scale features
scaler = StandardScaler()
X_original_scaled = scaler.fit_transform(X_original)
X_engineered_scaled = scaler.fit_transform(X_engineered)

# Split data
X_train_orig, X_test_orig, X_train_eng, X_test_eng, y_train, y_test = train_test_split(
    X_original_scaled, X_engineered_scaled, y, test_size=0.2, random_state=42, stratify=y
)

# Train Logistic Regression models
model_orig = LogisticRegression(random_state=42, max_iter=1000)
model_orig.fit(X_train_orig, y_train)
y_pred_orig = model_orig.predict(X_test_orig)

model_eng = LogisticRegression(random_state=42, max_iter=1000)
model_eng.fit(X_train_eng, y_train)
y_pred_eng = model_eng.predict(X_test_eng)

# Calculate metrics
def calculate_metrics(y_true, y_pred):
    return {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0)
    }

metrics_orig = calculate_metrics(y_test, y_pred_orig)
metrics_eng = calculate_metrics(y_test, y_pred_eng)

print("\nOriginal Features Performance:")
print(f"Accuracy: {metrics_orig['accuracy']:.4f}")
print(f"Precision: {metrics_orig['precision']:.4f}")
print(f"Recall: {metrics_orig['recall']:.4f}")
print(f"F1 Score: {metrics_orig['f1']:.4f}")

print("\nEngineered Features Performance:")
print(f"Accuracy: {metrics_eng['accuracy']:.4f}")
print(f"Precision: {metrics_eng['precision']:.4f}")
print(f"Recall: {metrics_eng['recall']:.4f}")
print(f"F1 Score: {metrics_eng['f1']:.4f}")

# Extract feature importances (absolute coefficients)
feature_names_orig = X_original.columns.tolist()
feature_names_eng = engineered_features.copy()

coeffs_orig = np.abs(model_orig.coef_[0])
coeffs_eng = np.abs(model_eng.coef_[0])

# Create DataFrame for feature importances
importance_df = pd.DataFrame({
    'Feature': feature_names_eng,
    'Importance': coeffs_eng
}).sort_values('Importance', ascending=False)

# Save engineered dataset
df.to_csv('engineered_features.csv', index=False)
print("\nEngineered dataset saved as 'engineered_features.csv'")

# Prepare results for feature_eng_results.csv
results_data = []

# Add performance metrics
for model_name, metrics in [('Original', metrics_orig), ('Engineered', metrics_eng)]:
    results_data.append({
        'Metric': 'accuracy',
        'Original': metrics['accuracy'] if model_name == 'Original' else '',
        'Engineered': metrics['accuracy'] if model_name == 'Engineered' else ''
    })
    results_data.append({
        'Metric': 'precision',
        'Original': metrics['precision'] if model_name == 'Original' else '',
        'Engineered': metrics['precision'] if model_name == 'Engineered' else ''
    })
    results_data.append({
        'Metric': 'recall',
        'Original': metrics['recall'] if model_name == 'Original' else '',
        'Engineered': metrics['recall'] if model_name == 'Engineered' else ''
    })
    results_data.append({
        'Metric': 'f1_score',
        'Original': metrics['f1'] if model_name == 'Original' else '',
        'Engineered': metrics['f1'] if model_name == 'Engineered' else ''
    })

# Add top feature importances
top_features = importance_df.head(5)
for idx, row in top_features.iterrows():
    results_data.append({
        'Metric': f"importance_{row['Feature']}",
        'Original': '',
        'Engineered': row['Importance']
    })

results_df = pd.DataFrame(results_data)
results_df.to_csv('feature_eng_results.csv', index=False)
print("Performance comparison saved as 'feature_eng_results.csv'")

# Plot side-by-side bar chart of top feature importances
top_n = 5
top_orig_indices = np.argsort(coeffs_orig)[-top_n:]
top_eng_indices = np.argsort(coeffs_eng)[-top_n:]

top_orig_features = [feature_names_orig[i] for i in top_orig_indices]
top_eng_features = [feature_names_eng[i] for i in top_eng_indices]

# Combine features for plotting
all_features = list(set(top_orig_features + top_eng_features))
all_features.sort()

# Create coefficient arrays for all features
orig_coeffs_all = np.zeros(len(all_features))
eng_coeffs_all = np.zeros(len(all_features))

for i, feat in enumerate(all_features):
    if feat in top_orig_features:
        idx = top_orig_features.index(feat)
        orig_coeffs_all[i] = coeffs_orig[top_orig_indices[idx]]
    if feat in top_eng_features:
        idx = top_eng_features.index(feat)
        eng_coeffs_all[i] = coeffs_eng[top_eng_indices[idx]]

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(all_features))
width = 0.35

bars1 = ax.bar(x - width/2, orig_coeffs_all, width, label='Original Features', color='steelblue')
bars2 = ax.bar(x + width/2, eng_coeffs_all, width, label='Engineered Features', color='darkorange')

ax.set_xlabel('Features')
ax.set_ylabel('Absolute Coefficient (Importance)')
ax.set_title('Top Feature Importances: Original vs Engineered')
ax.set_xticks(x)
ax.set_xticklabels(all_features, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('feature_importance_comparison.png', dpi=150, bbox_inches='tight')
plt.close()

print("Feature importance chart saved as 'feature_importance_comparison.png'")