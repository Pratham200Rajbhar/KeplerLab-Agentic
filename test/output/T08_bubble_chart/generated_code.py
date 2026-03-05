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
import random

# Set random seed for reproducibility
np.random.seed(42)

# Define continents and countries
continents = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania']
country_names = [
    'Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cameroon', 'Central African Republic', 'Chad',
    'Comoros', 'Congo', 'Djibouti', 'Egypt', 'Equatorial Guinea', 'Eritrea', 'Eswatini', 'Ethiopia', 'Gabon', 'Gambia',
    'Ghana', 'Guinea', 'Guinea-Bissau', 'Ivory Coast', 'Kenya', 'Lesotho', 'Liberia', 'Libya', 'Madagascar', 'Malawi',
    'Mali', 'Mauritania', 'Mauritius', 'Morocco', 'Mozambique', 'Namibia', 'Niger', 'Nigeria', 'Rwanda', 'Sao Tome and Principe',
    'Senegal', 'Seychelles', 'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan', 'Sudan', 'Tanzania', 'Togo', 'Tunisia',
    'Uganda', 'Zambia', 'Zimbabwe', 'Afghanistan', 'Armenia', 'Azerbaijan', 'Bahrain', 'Bangladesh', 'Bhutan', 'Brunei',
    'Cambodia', 'China', 'Cyprus', 'Georgia', 'India', 'Indonesia', 'Iran', 'Iraq', 'Israel', 'Japan',
    'Jordan', 'Kazakhstan', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Lebanon', 'Malaysia', 'Maldives', 'Mongolia', 'Myanmar',
    'Nepal', 'North Korea', 'Oman', 'Pakistan', 'Palestine', 'Philippines', 'Qatar', 'Russia', 'Saudi Arabia', 'Singapore',
    'South Korea', 'Sri Lanka', 'Syria', 'Taiwan', 'Tajikistan', 'Thailand', 'Timor-Leste', 'Turkey', 'Turkmenistan', 'United Arab Emirates',
    'Uzbekistan', 'Vietnam', 'Yemen', 'Albania', 'Andorra', 'Austria', 'Belarus', 'Belgium', 'Bosnia and Herzegovina', 'Bulgaria',
    'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
    'Iceland', 'Ireland', 'Italy', 'Kosovo', 'Latvia', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'Malta', 'Moldova',
    'Monaco', 'Montenegro', 'Netherlands', 'North Macedonia', 'Norway', 'Poland', 'Portugal', 'Romania', 'San Marino', 'Serbia',
    'Slovakia', 'Slovenia', 'Spain', 'Sweden', 'Switzerland', 'Ukraine', 'United Kingdom', 'Vatican City', 'Canada', 'Costa Rica',
    'Cuba', 'Dominica', 'Dominican Republic', 'El Salvador', 'Greenland', 'Grenada', 'Guatemala', 'Haiti', 'Honduras', 'Jamaica',
    'Mexico', 'Nicaragua', 'Panama', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Trinidad and Tobago', 'United States', 'Antigua and Barbuda', 'Argentina',
    'Bolivia', 'Brazil', 'Chile', 'Colombia', 'Ecuador', 'Guyana', 'Paraguay', 'Peru', 'Suriname', 'Uruguay',
    'Venezuela', 'Australia', 'Fiji', 'Kiribati', 'Marshall Islands', 'Micronesia', 'Nauru', 'New Zealand', 'Palau', 'Papua New Guinea',
    'Samoa', 'Solomon Islands', 'Tonga', 'Tuvalu', 'Vanuatu'
]

# Select 80 countries (first 80 in the list)
selected_countries = country_names[:80]

# Generate synthetic data
n_countries = 80
gdp = np.random.uniform(5, 2000, n_countries)  # GDP in billions USD
life_expectancy = np.random.uniform(55, 85, n_countries)  # Life Expectancy in years
population = np.random.uniform(0.5, 1400, n_countries)  # Population in millions

# Assign continents (ensure all continents are represented)
continent_assignments = []
for i in range(n_countries):
    continent_assignments.append(continents[i % len(continents)])

# Create DataFrame
df = pd.DataFrame({
    'Country': selected_countries,
    'GDP': gdp,
    'LifeExpectancy': life_expectancy,
    'Population': population,
    'Continent': continent_assignments
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

# Create bubble chart
plt.figure(figsize=(12, 8))

# Create color mapping for continents
colors = {
    'Africa': 'red',
    'Asia': 'blue',
    'Europe': 'green',
    'North America': 'orange',
    'South America': 'purple',
    'Oceania': 'brown'
}

# Plot bubbles
for continent in continents:
    mask = df['Continent'] == continent
    plt.scatter(
        df.loc[mask, 'GDP'],
        df.loc[mask, 'LifeExpectancy'],
        s=df.loc[mask, 'Population'] * 10,  # Scale population for visibility
        alpha=0.6,
        label=continent,
        color=colors[continent]
    )

# Add labels for top 5 countries by population
top5 = df.nlargest(5, 'Population')
for i, row in top5.iterrows():
    plt.annotate(
        row['Country'],
        (row['GDP'], row['LifeExpectancy']),
        textcoords="offset points",
        xytext=(5, 5),
        fontsize=9,
        ha='left'
    )

# Labels and title
plt.xlabel('GDP (billions USD)', fontsize=12)
plt.ylabel('Life Expectancy (years)', fontsize=12)
plt.title('Bubble Chart: GDP vs Life Expectancy with Population Size and Continent', fontsize=14)
plt.legend(title='Continent', loc='lower right')
plt.grid(True, alpha=0.3)

# Save the chart
plt.savefig('bubble_chart.png', dpi=150, bbox_inches='tight')
plt.close()

# Save the dataset to CSV
df.to_csv('synthetic_countries_data.csv', index=False)

print("\nBubble chart saved as 'bubble_chart.png'")
print("Synthetic data saved as 'synthetic_countries_data.csv'")