import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
import serial
import time

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

# Step 5: Create a colormap based on the magnitude
cmap = cm.viridis
norm = Normalize(vmin=magnitude.min(), vmax=magnitude.max())
colors = cmap(norm(magnitude))

# Step 6: Create a figure and axis for the plot
fig, ax = plt.subplots()

# Step 7: Plot the vector map with color representing the strength of the magnetic field
quiver_plot = ax.quiver(x_coords, y_coords, u, v, angles='xy', scale_units='xy', scale=50, color=colors, width=0.005)

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

# Step 12: Compute the Euclidean distance for each location's magnetic intensity
def calculate_distance(real_time_data, location_data):
    test_x, test_y, test_z = real_time_data
    distances = np.sqrt((location_data['M_X'] - test_x)**2 + (location_data['M_Y'] - test_y)**2 + (location_data['M_Z'] - test_z)**2)
    return distances

# Global variable to store the previous best match location
previous_best_match_location = None

def plot_real_time(real_time_data):
    global quiver_plot, previous_best_match_location

    # Step 13: Find the location with the minimum distance (best match)
    distances = calculate_distance(real_time_data, merged_data)
    best_match_index = np.argmin(distances)
    best_match_location = merged_data['Location'].iloc[best_match_index]
    print(f"The location that matches the test data is: {best_match_location}")

    # Update the plot only if the location changes
    if best_match_location != previous_best_match_location:
        previous_best_match_location = best_match_location

        # Step 14: Highlight the matching location with bold red color
        matching_x = x_coords.iloc[best_match_index]
        matching_y = y_coords.iloc[best_match_index]
        matching_u = u.iloc[best_match_index]
        matching_v = v.iloc[best_match_index]

        # Remove the previous quiver plot if it exists
        if hasattr(plot_real_time, 'highlight_quiver'):
            plot_real_time.highlight_quiver.remove()

        # Add a new quiver plot for the matching location
        plot_real_time.highlight_quiver = ax.quiver(matching_x, matching_y, matching_u, matching_v, angles='xy', scale_units='xy', scale=50, color='red', width=0.01)

        # Step 15: Show the plot
        plt.draw()  # Update the plot

def read_serial_data():
    # print("Reading serial data")
    global previous_location
    if ser.in_waiting > 0:
        real_time_data = ser.readline().decode('utf-8').rstrip()
        print(f"Raw serial data: {real_time_data}")

        # Split the data and convert to float
        try:
            real_time_data = [float(item) for item in real_time_data.split(',')]
            # print(f"Processed real-time data: {real_time_data}")

            # Indices to remove
            indices_to_remove = [3, 4, 5]  # Example indices to remove
            real_time_data = [item for idx, item in enumerate(real_time_data) if idx not in indices_to_remove]
            print(f"Processed real-time data: {real_time_data}")
            # Plot the real-time data
            plot_real_time(real_time_data)
        except ValueError as e:
            print(f"Error processing serial data: {e}")

#----------------------------Serial Port Section----------------------------

# Configure the serial port
ser = serial.Serial(
    port='COM10',        # Replace with your port name
    baudrate=9600,      # Set the baud rate
    timeout=1           # Set a timeout for reading
)
print("Serial port configured to COM10!")

#----------------------------Serial Port Section End----------------------------

plt.ion()  # Enable interactive mode

# Continuously read and process serial data
while True:
    read_serial_data()
    plt.pause(0.001)  # Pause to allow the plot to update