import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import serial

# Get input from the user for the starting and target locations
Starting_location = (input("Enter the starting location no: ")).strip()
Target_location = (input("Enter the target location no: ")).strip()
Starting_location = f"data_location_{Starting_location}"
Target_location = f"data_location_{Target_location}"
# print(f"Starting location: {Starting_location}")
# print(f"Target location: {Target_location}")


# Configure the serial port
ser = serial.Serial(
    port='COM10',        # Replace with your port name
    baudrate=9600,      # Set the baud rate
    timeout=1           # Set a timeout for reading
)
print("Serial port configured to COM10!")

# Load location map coordinates distances for calculate angle to turn to the final location
distances = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/map_coordinates_distances.csv")

# Load location map coordinates for mapping
coordinates = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/map_coordinates.csv")

# Load reference location dataset for calculate the Euclidean distance
ref_data = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations.csv")

# Get the (x, y) distances of the Starting_location
Starting_location = distances[distances['Location'] == Starting_location]
if not Starting_location.empty:
    x1, y1 = Starting_location.iloc[0]['X'], Starting_location.iloc[0]['Y']

# Get the (x, y) distances of the Target_location
Target_location = distances[distances['Location'] == Target_location]
if not Target_location.empty:
    x2, y2 = Target_location.iloc[0]['X'], Target_location.iloc[0]['Y']

print(f"Starting location: {Starting_location}")
print(f"Target location: {Target_location}")

# Calculate the angle to turn to the final location
# angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
# angle = angle if angle >= 0 else 360 + angle
# print(f"Angle to turn: {angle}")

# # Calculate the angle to turn to the final location in radians
angle = np.arctan2(y2 - y1, x2 - x1)
angle = angle if angle >= 0 else 2 * np.pi + angle
print(f"Angle to turn (radians): {angle}")

# Send data using serial port
command_to_send = "6"
ser.write(command_to_send.encode('utf-8'))
print(f"Sent: {command_to_send}")
ser.write(str(angle).encode('utf-8'))
print(f"Sent: {str(angle)}")
ser.write("\n".encode('utf-8'))

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