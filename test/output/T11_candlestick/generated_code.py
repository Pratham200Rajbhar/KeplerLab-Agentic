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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic stock data for 60 trading days
n_days = 60
start_price = 100.0

# Generate daily returns using a random walk with drift
drift = 0.0002  # slight upward drift
volatility = 0.02  # daily volatility

daily_returns = np.random.normal(loc=drift, scale=volatility, size=n_days)
prices = start_price * np.exp(np.cumsum(daily_returns))

# Create OHLCV data
open_prices = np.zeros(n_days)
close_prices = np.zeros(n_days)
high_prices = np.zeros(n_days)
low_prices = np.zeros(n_days)

open_prices[0] = start_price
close_prices[0] = start_price * (1 + daily_returns[0])
high_prices[0] = max(open_prices[0], close_prices[0]) * (1 + abs(daily_returns[0]) * 0.5)
low_prices[0] = min(open_prices[0], close_prices[0]) * (1 - abs(daily_returns[0]) * 0.5)

for i in range(1, n_days):
    open_prices[i] = close_prices[i-1]
    close_prices[i] = open_prices[i] * (1 + daily_returns[i])
    high_prices[i] = max(open_prices[i], close_prices[i]) * (1 + abs(daily_returns[i]) * 0.3)
    low_prices[i] = min(open_prices[i], close_prices[i]) * (1 - abs(daily_returns[i]) * 0.3)

# Generate volume data (higher on volatile days)
volume = np.round(100000 + np.abs(daily_returns) * 500000 + np.random.randint(0, 50000, n_days)).astype(int)

# Create DataFrame
dates = pd.date_range(start='2023-01-01', periods=n_days, freq='B')
df = pd.DataFrame({
    'Date': dates,
    'Open': open_prices,
    'High': high_prices,
    'Low': low_prices,
    'Close': close_prices,
    'Volume': volume
})
df.set_index('Date', inplace=True)

# Print dataset summary
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")
print("\nData types:")
print(df.dtypes)
print("\nDescriptive statistics:")
print(df.describe())

# Compute 20-day moving average
df['MA20'] = df['Close'].rolling(window=20).mean()

# Print key results
print(f"\nLast closing price: ${df['Close'].iloc[-1]:.2f}")
print(f"20-day moving average (last value): ${df['MA20'].iloc[-1]:.2f}")

# Prepare data for plotting
df_plot = df.copy()

# Create candlestick chart with volume using matplotlib
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})

# Candlestick plotting
def plot_candlestick(ax, df):
    width = 0.6
    for i in range(len(df)):
        date = mdates.date2num(df.index[i])
        open_price = df['Open'].iloc[i]
        close_price = df['Close'].iloc[i]
        high_price = df['High'].iloc[i]
        low_price = df['Low'].iloc[i]
        
        color = 'green' if close_price >= open_price else 'red'
        
        # Draw wick
        ax.plot([date, date], [low_price, high_price], color='black', linewidth=1)
        
        # Draw body
        ax.add_patch(plt.Rectangle((date - width/2, min(open_price, close_price)), 
                                   width, abs(close_price - open_price), 
                                   facecolor=color, edgecolor='black'))

plot_candlestick(ax1, df_plot)

# Plot moving average
ax1.plot(df_plot.index, df_plot['MA20'], color='blue', label='MA20', linewidth=1)
ax1.set_ylabel('Price ($)')
ax1.legend()
ax1.grid(True)

# Volume bar chart
colors = ['green' if df_plot['Close'].iloc[i] >= df_plot['Open'].iloc[i] else 'red' 
          for i in range(len(df_plot))]
ax2.bar(df_plot.index, df_plot['Volume'], color=colors, width=0.8, alpha=0.7)
ax2.set_ylabel('Volume')
ax2.grid(True)

plt.suptitle('Stock Price (Candlestick with Volume)', fontsize=14)
plt.tight_layout()

# Save the figure
plt.savefig('candlestick_chart.png', dpi=150, bbox_inches='tight')
plt.close()

# Save the data to CSV
df.to_csv('synthetic_stock_data.csv')
print("\nSynthetic stock data saved to 'synthetic_stock_data.csv'")
print("Candlestick chart saved to 'candlestick_chart.png'")