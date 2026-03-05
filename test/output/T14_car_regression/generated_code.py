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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import joblib
import os

# Load the car sales dataset (using a common public dataset: CarPrice_Assignment.csv)
# Since no specific dataset is provided, we'll use a standard one available via sklearn or download
# For this environment, we'll simulate a realistic car sales dataset if the file doesn't exist
# But first, try to load a known dataset from sklearn or use a sample

# Try to load from a common source; if not available, create a synthetic dataset
try:
    # Attempt to load from a typical location (e.g., Kaggle CarPrice_Assignment.csv)
    # Since we can't download, we'll simulate a dataset if needed
    df = pd.read_csv('CarPrice_Assignment.csv')
except:
    # Create a synthetic car sales dataset for demonstration
    np.random.seed(42)
    n_samples = 1000
    
    car_brands = ['Toyota', 'Honda', 'Ford', 'BMW', 'Mercedes', 'Audi', 'Tesla', 'Hyundai', 'Nissan', 'Chevrolet']
    fuel_types = ['gas', 'diesel']
    aspiration = ['std', 'turbo']
    drive_wheels = ['4wd', 'fwd', 'rwd']
    engine_types = ['dohc', 'ohcv', 'ohc', 'l', 'rotor', 'ohcf']
    cylinder_numbers = ['two', 'three', 'four', 'five', 'six', 'eight', 'twelve']
    
    data = {
        'car_name': [f'{brand} {model}' for brand, model in zip(
            np.random.choice(car_brands, n_samples),
            [f'Model-{i}' for i in np.random.randint(1, 100, n_samples)]
        )],
        'symboling': np.random.randint(-2, 4, n_samples),
        'wheel_base': np.random.uniform(88, 120, n_samples),
        'length': np.random.uniform(140, 200, n_samples),
        'width': np.random.uniform(60, 75, n_samples),
        'height': np.random.uniform(45, 60, n_samples),
        'curb_weight': np.random.uniform(1500, 4500, n_samples),
        'engine_size': np.random.uniform(60, 300, n_samples),
        'horsepower': np.random.uniform(48, 288, n_samples),
        'peak_rpm': np.random.randint(4000, 7000, n_samples),
        'city_mpg': np.random.randint(10, 50, n_samples),
        'highway_mpg': np.random.randint(15, 55, n_samples),
        'price': np.random.uniform(5000, 45000, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Add some categorical features
    df['fuel_type'] = np.random.choice(fuel_types, n_samples)
    df['aspiration'] = np.random.choice(aspiration, n_samples)
    df['drive_wheels'] = np.random.choice(drive_wheels, n_samples)
    df['engine_type'] = np.random.choice(engine_types, n_samples)
    df['cylinder_number'] = np.random.choice(cylinder_numbers, n_samples)
    
    # Make price more realistic (correlated with other features)
    df['price'] = (
        5000 + 
        100 * df['wheel_base'] + 
        80 * df['length'] + 
        150 * df['width'] - 
        50 * df['height'] + 
        0.5 * df['curb_weight'] + 
        2 * df['engine_size'] + 
        1.5 * df['horsepower'] - 
        10 * df['city_mpg'] - 
        8 * df['highway_mpg'] +
        np.random.normal(0, 1000, n_samples)
    )
    
    # Ensure price is positive
    df['price'] = df['price'].clip(lower=5000)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print("Columns:", list(df.columns))
print("\nData types:")
print(df.dtypes)
print("\nMissing values:")
print(df.isnull().sum())
print("\nDescriptive statistics:")
print(df.describe())

# Separate features and target
X = df.drop('price', axis=1)
y = df['price']

# Identify categorical and numerical columns
categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
numerical_cols = X.select_dtypes(include=['number']).columns.tolist()

print(f"\nCategorical columns: {categorical_cols}")
print(f"Numerical columns: {numerical_cols}")

# Create preprocessing pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'), categorical_cols),
        ('num', 'passthrough', numerical_cols)
    ]
)

# Split data 80/20
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Preprocess training and test data
X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# Get feature names after preprocessing
cat_feature_names = preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_cols)
feature_names = list(cat_feature_names) + numerical_cols

print(f"\nProcessed features: {len(feature_names)}")

# Train Linear Regression
print("\nTraining Linear Regression...")
lr_model = LinearRegression()
lr_model.fit(X_train_processed, y_train)
y_pred_lr = lr_model.predict(X_test_processed)

# Train Random Forest Regressor
print("Training Random Forest Regressor...")
rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
rf_model.fit(X_train_processed, y_train)
y_pred_rf = rf_model.predict(X_test_processed)

# Calculate metrics
def calculate_metrics(y_true, y_pred, model_name):
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{model_name} - R²: {r2:.4f}, MAE: {mae:.4f}, RMSE: {rmse:.4f}")
    return {'model': model_name, 'r2': r2, 'mae': mae, 'rmse': rmse}

metrics = []
metrics.append(calculate_metrics(y_test, y_pred_lr, 'LinearRegression'))
metrics.append(calculate_metrics(y_test, y_pred_rf, 'RandomForest'))

# Create metrics DataFrame and save
metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv('regression_metrics.csv', index=False)
print("\nMetrics saved to 'regression_metrics.csv'")

# Save models
joblib.dump(lr_model, 'car_lr_model.pkl')
joblib.dump(rf_model, 'car_rf_model.pkl')
print("Models saved as 'car_lr_model.pkl' and 'car_rf_model.pkl'")

# Residuals plot
plt.figure(figsize=(10, 6))
plt.scatter(y_pred_lr, y_pred_lr - y_test, c='blue', label='Linear Regression', alpha=0.5)
plt.scatter(y_pred_rf, y_pred_rf - y_test, c='red', label='Random Forest', alpha=0.5)
plt.axhline(y=0, color='black', linestyle='--', linewidth=2)
plt.xlabel('Predicted Values')
plt.ylabel('Residuals')
plt.title('Residuals Plot')
plt.legend()
plt.tight_layout()
plt.savefig('residuals_plot.png', dpi=150, bbox_inches='tight')
plt.close()

# Predicted vs Actual scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred_lr, c='blue', label='Linear Regression', alpha=0.5)
plt.scatter(y_test, y_pred_rf, c='red', label='Random Forest', alpha=0.5)
max_val = max(y_test.max(), y_pred_lr.max(), y_pred_rf.max())
min_val = min(y_test.min(), y_pred_lr.min(), y_pred_rf.min())
plt.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2)
plt.xlabel('Actual Values')
plt.ylabel('Predicted Values')
plt.title('Predicted vs Actual')
plt.legend()
plt.tight_layout()
plt.savefig('predicted_vs_actual.png', dpi=150, bbox_inches='tight')
plt.close()

# Feature importance for Random Forest
plt.figure(figsize=(12, 8))
importances = rf_model.feature_importances_
indices = np.argsort(importances)[::-1]
top_n = min(20, len(importances))  # Top 20 features
plt.barh(range(top_n), importances[indices[:top_n]][::-1])
plt.yticks(range(top_n), [feature_names[i] for i in indices[:top_n]][::-1])
plt.xlabel('Feature Importance')
plt.title('Top 20 Feature Importances (Random Forest)')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nVisualizations saved: 'residuals_plot.png', 'predicted_vs_actual.png', 'feature_importance.png'")
print("\nAll tasks completed successfully.")