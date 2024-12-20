import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import serial

# Configure the serial port
ser = serial.Serial(
    port='COM10',        # Replace with your port name
    baudrate=9600,      # Set the baud rate
    timeout=1           # Set a timeout for reading
)
print("Serial port configured to COM10!")

# Load location map coordinates for mapping
coordinates = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/map_coordinates.csv")

# Load reference location dataset for calculate the Euclidean distance
ref_data = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations.csv")

# Initialize Tkinter
root = tk.Tk()
root.title("Robot Localization")

# Load the map image
map_image = Image.open("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map.png")
map_photo = ImageTk.PhotoImage(map_image)

# Create a canvas to display the map
canvas = tk.Canvas(root, width=map_image.width, height=map_image.height)
canvas.pack()

# Add the map image to the canvas
canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)

# Function to update robot's position
def update_robot_position(location_name):
    # Clear the previous marker
    canvas.delete("robot_marker")
    # Get the (x, y) coordinates of the location
    location = coordinates[coordinates['Location'] == location_name]
    if not location.empty:
        x, y = location.iloc[0]['X'], location.iloc[0]['Y']
        # Place a new marker on the map
        canvas.create_oval(
            x - 5, y - 5, x + 5, y + 5, fill="red", tags="robot_marker"
        )
        print(f"Marker is placed at the location {location_name}")

# Function to compute Euclidean distance
def find_closest_location(real_time_data, ref_data):
    distances = []
    for index, row in ref_data.iterrows():
        distance = np.sqrt(
            (real_time_data[0] - row['M_X'])**2 +
            (real_time_data[1] - row['M_Y'])**2 +
            (real_time_data[2] - row['M_Z'])**2
        )
        distances.append((row['Location'], distance))
    # Sort by smallest distance
    distances.sort(key=lambda x: x[1])
    return distances[0][0]  # Return the closest location name

# Example real-time data
#real_time_data = [-31, -34, 43]

# Read data from the serial port
def read_serial_data():
    global previous_location
    if ser.in_waiting > 0:
        real_time_data = ser.readline().decode('utf-8').rstrip()
        #print(f"Received: {real_time_data}")

        # Split the data and convert to float
        real_time_data = [float(item) for item in real_time_data.split(',')]

        # Indices to remove
        indices_to_remove = [3, 4, 5]  # Example indices to remove
        real_time_data = [item for idx, item in enumerate(real_time_data) if idx not in indices_to_remove]
        #print(type(real_time_data))
        #print(real_time_data)
        
        # Find the closest location
        location = find_closest_location(real_time_data, ref_data)
        
        # Check if the location has changed
        if location != previous_location:
            print(f"The robot is at: {location}")
            update_robot_position(location)
            previous_location = location
    root.after(1, read_serial_data)  # Schedule the function to be called again after 1ms

previous_location = None
root.after(1, read_serial_data)  # Schedule the first call to read_serial_data
root.mainloop()