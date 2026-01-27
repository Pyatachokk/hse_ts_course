import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "python_sandbox"))

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from temp.plot_utils import create_standard_layout

# Generate synthetic time series with relative seasonal changes
# Example: Sales increase by 20% in December compared to November each year
np.random.seed(42)

# Parameters
n_years = 4
periods_per_year = 12  # Monthly data
n_points = n_years * periods_per_year

# Create time index
time = np.arange(n_points)
months = np.tile(np.arange(1, 13), n_years)  # 1-12 repeating for each year

# Create base level with moderate growth
base_level = 100 + 1.2 * time  # Linear trend

# Create seasonal component with relative changes
# For this example, we'll show a 20% increase in December (month 12) compared to November (month 11)
seasonal_multiplier = np.ones(n_points)

# Set December to be 20% higher than November
for year in range(n_years):
    # Find indices for November and December of this year
    nov_index = year * 12 + 10  # November is index 10 in 0-based array
    dec_index = year * 12 + 11  # December is index 11 in 0-based array
    
    # Set December to be 20% higher than the base level
    # While November stays at base level
    seasonal_multiplier[dec_index] = 1.2  # 20% increase

# Add some noise to make it more realistic
noise = np.random.normal(0, 5, n_points)

# Combine components to create the final series
y = base_level * seasonal_multiplier + noise

# Create the plot
fig = go.Figure()

# Add the time series
fig.add_trace(
    go.Scatter(
        x=time,
        y=y,
        mode="lines+markers",
        name="Продажи",
        line=dict(width=2),
        marker=dict(size=4),
    )
)

# Highlight December peaks with different color
december_indices = [i for i, month in enumerate(months) if month == 12]
november_indices = [i for i, month in enumerate(months) if month == 11]

fig.add_trace(
    go.Scatter(
        x=[time[i] for i in december_indices],
        y=[y[i] for i in december_indices],
        mode="markers",
        name="Декабрь (пик продаж)",
        marker=dict(size=8, color="red", symbol="star"),
    )
)

fig.add_trace(
    go.Scatter(
        x=[time[i] for i in november_indices],
        y=[y[i] for i in november_indices],
        mode="markers",
        name="Ноябрь (базовый уровень)",
        marker=dict(size=6, color="blue", symbol="diamond"),
    )
)

# Update layout with custom dimensions for a more horizontally stretched appearance
layout = create_standard_layout(
    title="",  # No title in the plot itself
    x_title="Время (месяцы)",
    y_title="Объем продаж",
)

# Modify layout for a more horizontally stretched appearance
layout.update(
    width=1000,  # Increased width
    height=400,  # Decreased height
    title=None,
)

fig.update_layout(**layout)

# Add vertical lines to indicate years
for i in range(1, n_years):
    fig.add_vline(x=i * periods_per_year, line_dash="dash", line_color="gray")

# Add annotations to explain the 20% increase
for year in range(n_years):
    dec_index = year * 12 + 11
    nov_index = year * 12 + 10
    
    # Add annotation showing the relative increase
    fig.add_annotation(
        x=time[dec_index],
        y=y[dec_index],
        text="↑ 20% выше",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="#636363",
        ax=20,
        ay=-30,
        bgcolor="white",
        bordercolor="#636363",
        borderwidth=1,
    )

# Save the plot with custom dimensions
# Ensure the images directory exists
os.makedirs("../chapters/images", exist_ok=True)

# Full path for the image
full_path = os.path.join("../chapters/images", "03_ETS_05_relative_changes.png")

# Save the plot
pio.write_image(
    fig,
    full_path,
    width=1000,  # Increased width
    height=400,  # Decreased height
    scale=2,
)

print(f"Plot saved successfully to {full_path}")