import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from temp.plot_utils import create_standard_layout

# Generate synthetic weekly time series with proportional seasonal fluctuations
np.random.seed(42)

# Parameters for weekly data with annual seasonality
n_years = 3
weeks_per_year = 52
n_points = n_years * weeks_per_year

# Create time index
time = np.arange(n_points)

# Create stable level (no trend)
base_level = 100

# Create seasonal pattern with higher mean and much higher variance in summer months
seasonal_means = []
seasonal_std = []

for week in range(weeks_per_year):
    # Create a strong seasonal pattern with peaks in summer
    # Summer weeks (20-35) have much higher mean
    if 20 <= week <= 35:  # Summer weeks
        mean_value = 150  # Much higher mean in summer
        std_value = 30  # Much higher variance in summer
    else:  # Winter and shoulder seasons
        mean_value = 80  # Lower mean in winter
        std_value = 10  # Lower variance in winter
    seasonal_means.append(mean_value)
    seasonal_std.append(std_value)

# Repeat the pattern for multiple years
seasonal_means = np.tile(seasonal_means, n_years)
seasonal_std = np.tile(seasonal_std, n_years)

# Generate data with proportional seasonal fluctuations
y = np.random.normal(seasonal_means, seasonal_std)

# Create the plot
fig = go.Figure()

# Add the time series
fig.add_trace(
    go.Scatter(
        x=time,
        y=y,
        mode="lines+markers",
        name="Временной ряд",
        line=dict(width=2),
        marker=dict(size=3),
    )
)

# Update layout with custom dimensions for a more horizontally stretched appearance
# Remove title since it will be provided in LaTeX caption
layout = create_standard_layout(
    title="",  # No title in the plot itself
    x_title="Время (недели)",
    y_title="Значение временного ряда",
)

# Modify layout for a more horizontally stretched appearance
layout.update(
    width=1000,  # Increased width
    height=400,  # Decreased height
    title=None,
)

fig.update_layout(**layout)

# Add horizontal line to show overall average level
fig.add_hline(y=100, line_dash="dot", line_color="red", opacity=0.7)

# Add vertical lines to indicate years
for i in range(1, n_years):
    fig.add_vline(x=i * weeks_per_year, line_dash="dash", line_color="gray")

# Save the plot with custom dimensions
# Ensure the images directory exists
os.makedirs("../chapters/images", exist_ok=True)

# Full path for the image
full_path = os.path.join(
    "../chapters/images", "03_ETS_01_weekly_proportional_seasonality.png"
)

# Save the plot
pio.write_image(
    fig,
    full_path,
    width=1000,  # Increased width
    height=400,  # Decreased height
    scale=2,
)

print(f"Plot saved successfully to {full_path}")
