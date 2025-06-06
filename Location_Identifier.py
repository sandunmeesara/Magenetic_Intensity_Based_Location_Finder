# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------
 
#                                      Author : Sandun Meesara Nakandala
#                                      Date   : 2024-12-31
#                                      Description : Location Identifier

# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------

import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import serial

#---------------------------Global Variables Section----------------------------
matched_location = ''
#---------------------------Global Variables Section End----------------------------

#----------------------------Functions Section----------------------------

# Function to select only nearest locations for calculate the Euclidean distance
def select_nearest_locations(distances,ref_data,template_size,matched_location):
    matched_location_x = distances[distances['Location'] == matched_location].iloc[0]['X']
    matched_location_y = distances[distances['Location'] == matched_location].iloc[0]['Y']
    selected_locations = distances[(distances['X'] >= matched_location_x - template_size) & (distances['X'] <= matched_location_x + template_size) & (distances['Y'] >= matched_location_y - template_size) & (distances['Y'] <= matched_location_y + template_size)]
    filtered_data = ref_data[ref_data['Location'].isin(selected_locations['Location'])]
    return filtered_data

# Function to update robot's position ----------------------------------------
def update_robot_position(location_name):
    # Clear the previous marker
    #canvas.delete("robot_marker")

    # Get the (x, y) coordinates of the location
    location = coordinates[coordinates['Location'] == location_name]
    if not location.empty:
        x, y = location.iloc[0]['X'], location.iloc[0]['Y']
        # Place a new marker on the map
        canvas.create_oval(
            x - 5, y - 5, x + 5, y + 5, fill="red", tags="robot_marker"
        )
        print(f"Marker is placed at the location {location_name}")

# Function to compute Euclidean distance ----------------------------------------
def find_closest_location(real_time_data, filtered_data):
    # matched_location_x = distances[distances['Location'] == matched_location].iloc[0]['X']
    # matched_location_y = distances[distances['Location'] == matched_location].iloc[0]['Y']
    # selected_locations = distances[(distances['X'] >= matched_location_x - template_size) & (distances['X'] <= matched_location_x + template_size) & (distances['Y'] >= matched_location_y - template_size) & (distances['Y'] <= matched_location_y + template_size)]
    # filtered_data = ref_data[ref_data['Location'].isin(selected_locations['Location'])]
    
    distances = []
    for index, row in filtered_data.iterrows():
        distance = np.sqrt(
            (real_time_data[0] - row['M_X'])**2 +
            (real_time_data[1] - row['M_Y'])**2 +
            (real_time_data[2] - row['M_Z'])**2
        )
        distances.append((row['Location'], distance))
    # Sort by smallest distance
    distances.sort(key=lambda x: x[1])
    return distances[0][0]  # Return the closest location name

# Fucntion to read data from the serial port ----------------------------------------
def read_serial_data():
    global previous_location
    global matched_location
    if ser.in_waiting > 0:
        try:
            real_time_data = ser.readline().decode('utf-8').rstrip()
            
            # Skip empty lines
            if not real_time_data:
                root.after(1, read_serial_data)
                return
                
            # Split the data and convert to float
            try:
                real_time_data = [float(item) for item in real_time_data.split(',') if item.strip()]
                
                # Check if we have enough data to process
                if len(real_time_data) < 3:  # We need at least 3 values (M_X, M_Y, M_Z)
                    root.after(1, read_serial_data)
                    return
                    
                # Indices to remove
                indices_to_remove = [3, 4, 5]  # Example indices to remove
                # Only remove indices if they exist in the data
                if len(real_time_data) > max(indices_to_remove):
                    real_time_data = [item for idx, item in enumerate(real_time_data) if idx not in indices_to_remove]
                
                # Select only nearest locations for calculate the Euclidean distance
                template_size = 1
                filtered_data = select_nearest_locations(distances, ref_data, template_size, matched_location)

                # Find the closest location
                location = find_closest_location(real_time_data, filtered_data)
                matched_location = location

                # Extract the location name from the DataFrame
                target_location_name = Target_location.iloc[0]['Location']

                # Check if the robot has reached the target location
                if (location == target_location_name):
                    print(f"Robot has reached the target location: {location}")
                    # Send data using serial port
                    command_to_send = "5"
                    ser.write(command_to_send.encode('utf-8'))
                    print(f"Sent: {command_to_send}")
                    ser.write("\n".encode('utf-8'))
                    return
                
                # Check if the location has changed
                if location != previous_location:
                    print(f"The robot is at: {location}")
                    update_robot_position(location)
                    previous_location = location
            except ValueError as e:
                print(f"Error parsing data: {e}")
                print(f"Received data: '{real_time_data}'")
        except Exception as e:
            print(f"Error reading serial data: {e}")
    
    root.after(1, read_serial_data)  # Schedule the function to be called again after 1ms

#----------------------------Functions Section End----------------------------

#----------------------------Serial Port Section----------------------------

# Configure the serial port
ser = serial.Serial(
    port='COM10',        # Replace with your port name
    baudrate=9600,      # Set the baud rate
    timeout=1           # Set a timeout for reading
)
print("Serial port configured to COM10!")

#----------------------------Serial Port Section End----------------------------

#----------------------------Data Section----------------------------

# Load location map coordinates distances for calculate angle to turn to the final location
distances = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Tile_Coordinates.csv")

# Load location map coordinates for mapping
coordinates = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Map_Image_Pixel_Coordinates_for_Locations.csv")

# Load reference location dataset for calculate the Euclidean distance
ref_data = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Magnetic_Data.csv")

#----------------------------Data Section End----------------------------

#----------------------------User Input Section----------------------------

# Get input from the user for the starting and target locations
Starting_location = (input("Enter the starting location no: ")).strip()
matched_location = "data_location_" + str(Starting_location)
Target_location = (input("Enter the target location no: ")).strip()
Starting_location = f"data_location_{Starting_location}"
Target_location = f"data_location_{Target_location}"
# print(f"Starting location: {Starting_location}")
# print(f"Target location: {Target_location}")

#----------------------------User Input Section End----------------------------

#----------------------------GUI Section----------------------------

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

#----------------------------GUI Section End----------------------------

#----------------------------Main Section----------------------------

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
angle_degrees = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
angle_degrees = angle_degrees if angle_degrees >= 0 else 360 + angle_degrees
print(f"Angle to turn: {angle_degrees}")

# # Calculate the angle to turn to the final location in radians
angle = np.arctan2(y2 - y1, x2 - x1)
angle = angle if angle >= 0 else 2 * np.pi + angle
print(f"Angle to turn (radians): {angle}")

# Send data using serial port
command_to_send = "t" + str(angle)
ser.write(command_to_send.encode('utf-8'))
print(f"Sent: {command_to_send}")
# ser.write(str(angle).encode('utf-8'))
# print(f"Sent: {str(angle)}")
# ser.write("\n".encode('utf-8'))

# Initialize the previous location
previous_location = None
root.after(1, read_serial_data)  # Schedule the first call to read_serial_data
root.mainloop()

#----------------------------Main Section End----------------------------