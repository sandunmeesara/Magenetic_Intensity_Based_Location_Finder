import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize

# Step 1: Load the data
location_data = pd.read_csv('e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations.csv')  # Modify with the actual file path
magnetic_data = pd.read_csv('e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/map_coordinates_distances.csv')  # Modify with the actual file path

# Step 2: Merge the data on 'Location'
merged_data = pd.merge(location_data, magnetic_data, on='Location')

# Step 3: Extract x, y coordinates and magnetic intensity components (x, y, z)
x_coords = merged_data['X']
y_coords = merged_data['Y']
u = merged_data['M_X']  # X-component of magnetic intensity
v = merged_data['M_Y']  # Y-component of magnetic intensity

# Step 4: Calculate the magnitude of the magnetic intensity (strength)
magnitude = np.sqrt(u**2 + v**2)

# Step 5: Normalize the magnitude for color mapping
norm = Normalize(vmin=magnitude.min(), vmax=magnitude.max())

# Step 6: Create a colormap and apply it to the magnitude values
cmap = cm.plasma  # Use 'plasma' colormap
colors = cmap(norm(magnitude))

# Step 7: Plot the vector map with color representing the strength of the magnetic field
fig, ax = plt.subplots(figsize=(10, 8))  # Create a figure and axis object

# Reduce the scale to make the arrows smaller
scale_factor = 50  # Adjust this to change the size of arrows (lower value for smaller arrows)

quiver_plot = ax.quiver(x_coords, y_coords, u, v, angles='xy', scale_units='xy', scale=scale_factor, color=colors, width=0.005)

# Adding labels and title
ax.set_title("Magnetic Intensity Vector Map (Direction and Strength)")
ax.set_xlabel("X-coordinate")
ax.set_ylabel("Y-coordinate")

# Optional: Add a grid for better visualization
ax.grid(True)

# Step 8: Create a ScalarMappable to link colormap and normalize, and add the colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])  # Set empty array since no data is passed for the colorbar
fig.colorbar(sm, ax=ax, label='Magnetic Field Strength')

# Step 9: Add location numbers (removing "data_location_" prefix)
for i, location_name in enumerate(merged_data['Location']):
    # Remove the "data_location_" prefix from the location name
    location_number = location_name.replace("data_location_", "")
    ax.text(x_coords.iloc[i], y_coords.iloc[i], location_number, fontsize=9)

# Step 10: Adjust the plot limits to fit all arrows
padding = 1  # Add some padding to the plot area
ax.set_xlim([x_coords.min() - padding, x_coords.max() + padding])
ax.set_ylim([y_coords.min() - padding, y_coords.max() + padding])

# Optional: Make sure the aspect ratio is equal to avoid distortion
ax.set_aspect('equal')

# Step 11: Show the plot
plt.show()
