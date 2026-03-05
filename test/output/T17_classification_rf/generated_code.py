import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, precision_recall_fscore_support
import pickle
import warnings
warnings.filterwarnings('ignore')

# Load dataset (using built-in sample from sklearn if available, otherwise simulate)
try:
    from sklearn.datasets import fetch_openml
    dataset = fetch_openml(name='Social_Network_Ads', version=1, as_frame=True, parser='pandas')
    df = dataset.frame
except:
    # Fallback: simulate dataset with same structure
    np.random.seed(42)
    n = 400
    df = pd.DataFrame({
        'User ID': range(1, n+1),
        'Gender': np.random.choice(['Male', 'Female'], n),
        'Age': np.random.randint(18, 70, n),
        'EstimatedSalary': np.random.randint(15000, 150000, n),
        'Purchased': np.random.randint(0, 2, n)
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

# Encode Gender
le = LabelEncoder()
df['Gender'] = le.fit_transform(df['Gender'])

# Features and target
X = df[['Gender', 'Age', 'EstimatedSalary']]
y = df['Purchased']

# Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train-test split (80/20)
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

# Train Random Forest
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# Predictions
y_pred = rf.predict(X_test)
y_proba = rf.predict_proba(X_test)[:, 1]

# Evaluation metrics
accuracy = rf.score(X_test, y_test)
precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary')

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1 Score: {f1:.4f}")

# Classification report
report = classification_report(y_test, y_pred, output_dict=True)
report_df = pd.DataFrame(report).transpose()
report_df.to_csv('classification_report.csv', index=True)

# Confusion matrix plot
plt.figure(figsize=(6,5))
sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.ylabel('Actual')
plt.xlabel('Predicted')
plt.savefig('confusion_matrix.png', bbox_inches='tight')
plt.close()

# Feature importance plot
feature_names = ['Gender', 'Age', 'EstimatedSalary']
importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]
plt.figure(figsize=(8,5))
plt.bar(range(len(importances)), importances[indices], align='center')
plt.xticks(range(len(importances)), [feature_names[i] for i in indices])
plt.title('Feature Importance')
plt.ylabel('Importance')
plt.savefig('feature_importance.png', bbox_inches='tight')
plt.close()

# ROC curve plot
fpr, tpr, _ = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)
plt.figure(figsize=(6,5))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc="lower right")
plt.savefig('roc_curve.png', bbox_inches='tight')
plt.close()

# Save model and scaler
with open('rf_model.pkl', 'wb') as f:
    pickle.dump({'model': rf, 'scaler': scaler, 'label_encoder': le}, f)

print("\nAll outputs saved: confusion_matrix.png, feature_importance.png, roc_curve.png, classification_report.csv, rf_model.pkl")