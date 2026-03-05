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
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import scipy.stats as stats
import joblib

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic housing dataset
n_samples = 1000
size_sqft = np.random.uniform(500, 4000, n_samples)
bedrooms = np.random.randint(1, 7, n_samples)
bathrooms = np.random.randint(1, 5, n_samples)
age_years = np.random.uniform(0, 50, n_samples)
distance_city_km = np.random.uniform(0.5, 30, n_samples)

# Generate price with realistic relationships and noise
price = (
    150 * size_sqft +
    10000 * bedrooms +
    15000 * bathrooms -
    2000 * age_years -
    5000 * distance_city_km +
    np.random.normal(0, 30000, n_samples)
)

# Create DataFrame
df = pd.DataFrame({
    'size_sqft': size_sqft,
    'bedrooms': bedrooms,
    'bathrooms': bathrooms,
    'age_years': age_years,
    'distance_city_km': distance_city_km,
    'price': price
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

# Prepare features and target
X = df.drop('price', axis=1)
y = df['price']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train LinearRegression model
model = LinearRegression()
model.fit(X_train, y_train)

# Make predictions
y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)

# Calculate metrics
train_r2 = r2_score(y_train, y_train_pred)
test_r2 = r2_score(y_test, y_test_pred)
train_mae = mean_absolute_error(y_train, y_train_pred)
test_mae = mean_absolute_error(y_test, y_test_pred)
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))

# Print metrics
print(f"\nTraining R²: {train_r2:.4f}")
print(f"Test R²: {test_r2:.4f}")
print(f"Training MAE: ${train_mae:.2f}")
print(f"Test MAE: ${test_mae:.2f}")
print(f"Training RMSE: ${train_rmse:.2f}")
print(f"Test RMSE: ${test_rmse:.2f}")

# Calculate residuals
residuals = y_test - y_test_pred

# Create and save visualizations

# 1. Residuals vs Predicted plot
plt.figure(figsize=(8, 6))
plt.scatter(y_test_pred, residuals, alpha=0.7)
plt.axhline(y=0, color='r', linestyle='--')
plt.xlabel('Predicted Price')
plt.ylabel('Residuals')
plt.title('Residuals vs Predicted Values')
plt.savefig('residuals_vs_predicted.png', dpi=150, bbox_inches='tight')
plt.close()

# 2. Q-Q plot of residuals
plt.figure(figsize=(8, 6))
stats.probplot(residuals, dist="norm", plot=plt)
plt.title('Q-Q Plot of Residuals')
plt.savefig('qq_plot_residuals.png', dpi=150, bbox_inches='tight')
plt.close()

# 3. Predicted vs Actual scatter plot
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_test_pred, alpha=0.7)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
plt.xlabel('Actual Price')
plt.ylabel('Predicted Price')
plt.title('Predicted vs Actual Values')
plt.savefig('predicted_vs_actual.png', dpi=150, bbox_inches='tight')
plt.close()

# 4. Coefficient bar chart
coefficients = model.coef_
feature_names = X.columns
plt.figure(figsize=(10, 6))
plt.bar(feature_names, coefficients)
plt.xlabel('Features')
plt.ylabel('Coefficient Value')
plt.title('Linear Regression Coefficients')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('coefficient_bar_chart.png', dpi=150, bbox_inches='tight')
plt.close()

# Save model
joblib.dump(model, 'linear_regression.pkl')

# Save metrics to CSV
metrics_df = pd.DataFrame({
    'Metric': ['R²', 'MAE', 'RMSE'],
    'Training': [train_r2, train_mae, train_rmse],
    'Test': [test_r2, test_mae, test_rmse]
})
metrics_df.to_csv('lr_metrics.csv', index=False)

print("\nModel saved as 'linear_regression.pkl'")
print("Metrics saved as 'lr_metrics.csv'")
print("Visualizations saved: residuals_vs_predicted.png, qq_plot_residuals.png, predicted_vs_actual.png, coefficient_bar_chart.png")