import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "python_sandbox"))

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from temp.plot_utils import create_standard_layout

# Generate synthetic time series with proportional seasonal fluctuations
np.random.seed(42)

# Parameters - longer time series
n_years = 5  # Increased from 3 to 5 years
periods_per_year = 12  # Monthly data
n_points = n_years * periods_per_year

# Create time index
time = np.arange(n_points)

# Create trend component with stronger growth
trend = 100 + 2.5 * time  # Increased trend coefficient from 1.5 to 2.5

# Create seasonal component with proportional fluctuations
# High season: +50% of current level, Low season: -30% of current level
# More pronounced seasonal pattern
seasonal_base = np.tile(
    [1.5, 1.4, 1.2, 0.8, 0.6, 0.7, 0.9, 1.1, 1.3, 1.6, 1.5, 1.3], n_years
)

# Add some noise
noise = np.random.normal(0, 8, n_points)  # Increased noise from 5 to 8

# Combine components to create the final series with proportional seasonality
# The seasonal effect is proportional to the trend level
y = trend * seasonal_base + noise

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
        marker=dict(size=4),
    )
)

# Update layout with custom dimensions for a more horizontally stretched appearance
# Remove title since it will be provided in LaTeX caption
layout = create_standard_layout(
    title="",  # No title in the plot itself
    x_title="Время (месяцы)",
    y_title="Значение временного ряда",
)

# Modify layout for a more horizontally stretched appearance
layout.update(
    width=1000,  # Increased width
    height=400,  # Decreased height
    # Remove title font settings since there's no title
    title=None,
)

fig.update_layout(**layout)

# Add vertical lines to indicate years
for i in range(1, n_years):
    fig.add_vline(x=i * periods_per_year, line_dash="dash", line_color="gray")

# Save the plot with custom dimensions
# Ensure the images directory exists
os.makedirs("../chapters/images", exist_ok=True)

# Full path for the image
full_path = os.path.join("../chapters/images", "03_ETS_02_increasing_volatility.png")

# Save the plot
pio.write_image(
    fig,
    full_path,
    width=1000,  # Increased width
    height=400,  # Decreased height
    scale=2,
)

print(f"Plot saved successfully to {full_path}")
