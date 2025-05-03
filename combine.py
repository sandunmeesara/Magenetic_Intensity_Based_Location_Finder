import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import serial
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class CombinedLocationVisualization:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Location & Magnetic Vector Visualization")
        
        # Set a fixed size to ensure all components are visible
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)  # Set minimum window size
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure styles
        style = ttk.Style()
        style.configure("Accent.TButton", font=('TkDefaultFont', 10, 'bold'))
        
        # Initialize global variables
        self.matched_location = ''
        self.previous_location = None
        self.vector = [0, 0, 0]  # Initialize vector with default values
        self.history = []
        self.max_history = 100
        
        # Serial connection parameters
        self.serial_port = None
        self.is_connected = False
        self.stop_thread = False
        self.serial_thread = None
        
        # Load data
        self.load_data()
        
        # Create the main vertical container to organize the layout
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top frame for visualizations - set fixed height
        self.top_frame = ttk.Frame(self.main_container)
        self.top_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Force the top frame to have minimum height
        self.top_frame.configure(height=600)
        self.top_frame.pack_propagate(False)
        
        # Create bottom frame for controls - fixed height
        self.bottom_frame = ttk.LabelFrame(self.main_container, text="Control Panel")
        self.bottom_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        self.bottom_frame.configure(height=180)
        self.bottom_frame.pack_propagate(False)
        
        # Split the top frame into left and right using a paned window
        self.top_paned = ttk.PanedWindow(self.top_frame, orient=tk.HORIZONTAL)
        self.top_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for map
        self.left_panel = ttk.Frame(self.top_paned)
        self.top_paned.add(self.left_panel, weight=1)
        
        # Right panel for vector visualization
        self.right_panel = ttk.Frame(self.top_paned)
        self.top_paned.add(self.right_panel, weight=1)
        
        # Setup panels - with fixed panel sizes
        self.setup_map_panel()
        self.setup_vector_panel()
        self.setup_control_panel()
        
        # Initial plot update
        self.update_vector_plot()
        
        # Force the window to update and show all components
        self.root.update_idletasks()
    
    def load_data(self):
        """Load all required data files"""
        try:
            # Load location map coordinates for distance calculation
            self.distances = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Tile_Coordinates.csv")
            
            # Load location map coordinates for mapping
            self.coordinates = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Map_Image_Pixel_Coordinates_for_Locations.csv")
            
            # Load reference location dataset for Euclidean distance calculation
            self.ref_data = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Magnetic_Data.csv")
        except Exception as e:
            messagebox.showerror("Data Loading Error", f"Failed to load data files: {str(e)}")
            raise
    
    def setup_map_panel(self):
        """Set up the map visualization panel"""
        # Create frame for map display with a label
        self.map_frame = ttk.LabelFrame(self.left_panel, text="Map Visualization")
        self.map_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Load the map image
        self.map_image = Image.open("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map.png")
        
        # Resize the image if it's too large
        max_width = 600
        max_height = 500
        if self.map_image.width > max_width or self.map_image.height > max_height:
            ratio = min(max_width / self.map_image.width, max_height / self.map_image.height)
            new_width = int(self.map_image.width * ratio)
            new_height = int(self.map_image.height * ratio)
            self.map_image = self.map_image.resize((new_width, new_height), Image.LANCZOS)
        
        self.map_photo = ImageTk.PhotoImage(self.map_image)
        
        # Create a canvas to display the map
        self.map_canvas = tk.Canvas(self.map_frame, width=self.map_image.width, height=self.map_image.height)
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add the map image to the canvas
        self.map_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
        
        # Add a label to confirm the map panel is visible
        ttk.Label(self.map_frame, text="Map Panel", font=('Arial', 12, 'bold')).pack(side=tk.BOTTOM)
    
    def setup_vector_panel(self):
        """Set up the 3D vector visualization panel"""
        # Create frame for vector visualization with a label
        self.vector_frame = ttk.LabelFrame(self.right_panel, text="Magnetic Vector Visualization")
        self.vector_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a conspicuous label at the top
        ttk.Label(self.vector_frame, text="VECTOR VISUALIZATION", background='yellow', font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Create figure and 3D axis
        self.fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set axis labels
        self.ax.set_xlabel('X (μT)')
        self.ax.set_ylabel('Y (μT)')
        self.ax.set_zlabel('Z (μT)')
        
        # Set plot title
        self.ax.set_title('Magnetic Vector')
        
        # Set axis limits with some padding
        self.ax.set_xlim([-100, 100])
        self.ax.set_ylim([-100, 100])
        self.ax.set_zlim([-100, 100])
        
        # Draw grid
        self.ax.grid(True)
        
        # Draw coordinate axes
        self.draw_coordinate_axes()
        
        # Embed the plot in the tkinter window
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.vector_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create vector info frame
        self.vector_info_frame = ttk.LabelFrame(self.right_panel, text="Vector Information")
        self.vector_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a grid for vector information
        self.vector_grid = ttk.Frame(self.vector_info_frame)
        self.vector_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # X component display
        ttk.Label(self.vector_grid, text="X:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.x_var = tk.StringVar(value="0.00")
        ttk.Label(self.vector_grid, textvariable=self.x_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Y component display
        ttk.Label(self.vector_grid, text="Y:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.y_var = tk.StringVar(value="0.00")
        ttk.Label(self.vector_grid, textvariable=self.y_var).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Z component display
        ttk.Label(self.vector_grid, text="Z:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.z_var = tk.StringVar(value="0.00")
        ttk.Label(self.vector_grid, textvariable=self.z_var).grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # Magnitude display
        ttk.Label(self.vector_grid, text="Magnitude:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.mag_var = tk.StringVar(value="0.00")
        ttk.Label(self.vector_grid, textvariable=self.mag_var).grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
        
        # Visualization options
        self.viz_options_frame = ttk.Frame(self.vector_info_frame)
        self.viz_options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Show history checkbox
        self.show_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.viz_options_frame, text="Show History", variable=self.show_history_var, 
                        command=self.update_vector_plot).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Show projections checkbox
        self.show_proj_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.viz_options_frame, text="Show Projections", variable=self.show_proj_var, 
                        command=self.update_vector_plot).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Auto-adjust scale checkbox
        self.auto_scale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.viz_options_frame, text="Auto-adjust Scale", variable=self.auto_scale_var, 
                        command=self.update_vector_plot).pack(side=tk.LEFT, padx=5, pady=5)
    
    def setup_control_panel(self):
        """Set up the bottom control panel with serial connection and location input"""
        # Add a conspicuous label at the top of the control panel
        ttk.Label(self.bottom_frame, text="CONTROL PANEL", background='yellow', 
                 font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Make the bottom panel more visible with a border and background
        self.bottom_frame.configure(borderwidth=2, relief="ridge")
        
        # Serial connection frame
        self.conn_frame = ttk.LabelFrame(self.bottom_frame, text="Serial Connection")
        self.conn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # COM Port selection
        ttk.Label(self.conn_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM10")  # Default port
        self.port_entry = ttk.Entry(self.conn_frame, width=10, textvariable=self.port_var)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Baud Rate selection
        ttk.Label(self.conn_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.IntVar(value=9600)  # Default baud rate
        baud_options = [9600, 19200, 38400, 57600, 115200]
        self.baud_combo = ttk.Combobox(self.conn_frame, width=8, textvariable=self.baud_var, values=baud_options)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Connect/Disconnect button
        self.conn_button = ttk.Button(self.conn_frame, text="Connect", command=self.toggle_connection)
        self.conn_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Location entry frame - IMPROVED VISIBILITY
        self.location_frame = ttk.LabelFrame(self.bottom_frame, text="Location Settings")
        self.location_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create a bold style for labels
        bold_style = ttk.Style()
        bold_style.configure("Bold.TLabel", font=('TkDefaultFont', 10, 'bold'))
        
        # Starting location - IMPROVED VISIBILITY
        ttk.Label(self.location_frame, text="Starting Location No:", style="Bold.TLabel").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_loc_var = tk.StringVar()
        self.start_loc_entry = ttk.Entry(self.location_frame, width=12, textvariable=self.start_loc_var, 
                                        font=('TkDefaultFont', 10))
        self.start_loc_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Target location - IMPROVED VISIBILITY
        ttk.Label(self.location_frame, text="Target Location No:", style="Bold.TLabel").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.target_loc_var = tk.StringVar()
        self.target_loc_entry = ttk.Entry(self.location_frame, width=12, textvariable=self.target_loc_var,
                                         font=('TkDefaultFont', 10))
        self.target_loc_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Set locations button - IMPROVED VISIBILITY
        self.set_locations_button = ttk.Button(self.location_frame, text="Set Locations", 
                                             command=self.set_locations,
                                             style="Accent.TButton")
        self.set_locations_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Instruction label
        ttk.Label(self.location_frame, text="Enter location numbers and click 'Set Locations'", 
                 wraplength=150, justify=tk.CENTER, foreground="blue").grid(
            row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # Status and log frame
        self.log_frame = ttk.LabelFrame(self.bottom_frame, text="System Log")
        self.log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a scrolled text widget for logs
        self.log_text = tk.Text(self.log_frame, height=5, width=50)
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=5)
        
        # Status indicator
        self.status_frame = ttk.Frame(self.bottom_frame)
        self.status_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="Current Location:")
        self.status_label.pack(padx=5, pady=5)
        
        self.current_loc_var = tk.StringVar(value="Not set")
        self.current_loc_label = ttk.Label(self.status_frame, textvariable=self.current_loc_var, font=('Arial', 12, 'bold'))
        self.current_loc_label.pack(padx=5, pady=5)
        
        # Log the startup message with instructions
        self.log_message("Application started. Please follow these steps:")
        self.log_message("1. Connect to the serial port")
        self.log_message("2. Enter starting and target location numbers in the Location Settings panel")
        self.log_message("3. Click 'Set Locations' to initialize the navigation")
    
    def draw_coordinate_axes(self):
        """Draw the coordinate axes in the 3D plot"""
        # X-axis in red
        self.ax.plot([0, 50], [0, 0], [0, 0], color='red', linewidth=2)
        # Y-axis in green
        self.ax.plot([0, 0], [0, 50], [0, 0], color='green', linewidth=2)
        # Z-axis in blue
        self.ax.plot([0, 0], [0, 0], [0, 50], color='blue', linewidth=2)
        
        # Label the axes
        self.ax.text(55, 0, 0, "X", color='red', fontsize=12)
        self.ax.text(0, 55, 0, "Y", color='green', fontsize=12)
        self.ax.text(0, 0, 55, "Z", color='blue', fontsize=12)
    
    def toggle_connection(self):
        """Connect to or disconnect from the serial port"""
        if not self.is_connected:
            try:
                port = self.port_var.get()
                baud = self.baud_var.get()
                
                # Try to open the serial port
                self.serial_port = serial.Serial(port=port, baudrate=baud, timeout=1)
                self.is_connected = True
                self.conn_button.config(text="Disconnect")
                self.log_message(f"Connected to {port} at {baud} baud")
                
                # Start the serial reading thread
                self.stop_thread = False
                self.serial_thread = threading.Thread(target=self.read_serial_data)
                self.serial_thread.daemon = True
                self.serial_thread.start()
                
                # Start animation
                self.start_animation()
                
            except Exception as e:
                messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
                self.is_connected = False
        else:
            # Disconnect
            self.stop_thread = True
            if self.serial_thread:
                self.serial_thread.join(timeout=1.0)
            
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.is_connected = False
            self.conn_button.config(text="Connect")
            self.log_message("Disconnected from serial port")
            
            # Stop animation
            if hasattr(self, 'ani') and self.ani is not None:
                self.ani.event_source.stop()
    
    def start_animation(self):
        """Start the animation for real-time updates"""
        self.ani = FuncAnimation(
            self.fig, 
            self._animate, 
            interval=100,  # Update every 100 ms
            blit=False
        )
    
    def _animate(self, i):
        """Animation function for FuncAnimation"""
        self.update_vector_plot()
        return []
    
    def set_locations(self):
        """Set the starting and target locations"""
        try:
            # Get input from the user for the starting and target locations
            starting_loc_num = self.start_loc_var.get().strip()
            target_loc_num = self.target_loc_var.get().strip()
            
            # Debug - show what was entered
            self.log_message(f"Input received - Starting: '{starting_loc_num}', Target: '{target_loc_num}'")
            
            if not starting_loc_num or not target_loc_num:
                messagebox.showerror("Input Error", "Please enter both starting and target location numbers.")
                return
            
            self.matched_location = f"data_location_{starting_loc_num}"
            start_location = f"data_location_{starting_loc_num}"
            target_location = f"data_location_{target_loc_num}"
            
            # Get the (x, y) distances of the Starting_location
            starting_location_data = self.distances[self.distances['Location'] == start_location]
            if starting_location_data.empty:
                messagebox.showerror("Location Error", f"Starting location {start_location} not found in data.")
                return
            x1, y1 = starting_location_data.iloc[0]['X'], starting_location_data.iloc[0]['Y']

            # Get the (x, y) distances of the Target_location
            target_location_data = self.distances[self.distances['Location'] == target_location]
            if target_location_data.empty:
                messagebox.showerror("Location Error", f"Target location {target_location} not found in data.")
                return
            x2, y2 = target_location_data.iloc[0]['X'], target_location_data.iloc[0]['Y']
            
            self.Starting_location = starting_location_data
            self.Target_location = target_location_data
            
            self.log_message(f"Starting location set to: {start_location}")
            self.log_message(f"Target location set to: {target_location}")
            
            # Calculate the angle to turn to the final location
            angle_degrees = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angle_degrees = angle_degrees if angle_degrees >= 0 else 360 + angle_degrees
            self.log_message(f"Angle to turn: {angle_degrees:.2f} degrees")
            
            # Calculate the angle in radians
            angle = np.arctan2(y2 - y1, x2 - x1)
            angle = angle if angle >= 0 else 2 * np.pi + angle
            
            # Send data using serial port if connected
            if self.is_connected and self.serial_port and self.serial_port.is_open:
                command_to_send = f"t{angle}"
                self.serial_port.write(command_to_send.encode('utf-8'))
                self.log_message(f"Sent command: {command_to_send}")
            else:
                self.log_message("Serial port not connected. Cannot send command.")
            
            # Update the map with markers
            self.update_map(starting_location_data, target_location_data)
            
        except Exception as e:
            messagebox.showerror("Set Locations Error", f"Error setting locations: {str(e)}")
    
    def update_map(self, starting_location, target_location):
        """Update the map with markers for starting and target locations"""
        # Clear previous markers
        self.map_canvas.delete("location_marker")
        
        # Place starting location marker (blue)
        x1, y1 = starting_location.iloc[0]['X'], starting_location.iloc[0]['Y']
        self.map_canvas.create_oval(
            x1 - 8, y1 - 8, x1 + 8, y1 + 8, 
            fill="blue", outline="black", tags="location_marker"
        )
        self.map_canvas.create_text(
            x1, y1 - 15, text="Start", fill="blue", font=("Arial", 10, "bold"), 
            tags="location_marker"
        )
        
        # Place target location marker (green)
        x2, y2 = target_location.iloc[0]['X'], target_location.iloc[0]['Y']
        self.map_canvas.create_oval(
            x2 - 8, y2 - 8, x2 + 8, y2 + 8, 
            fill="green", outline="black", tags="location_marker"
        )
        self.map_canvas.create_text(
            x2, y2 - 15, text="Target", fill="green", font=("Arial", 10, "bold"), 
            tags="location_marker"
        )
        
        # Draw a line between start and target
        self.map_canvas.create_line(
            x1, y1, x2, y2, fill="gray", dash=(4, 2), width=2, 
            arrow=tk.LAST, tags="location_marker"
        )
    
    def update_robot_position(self, location_name):
        """Update the robot's position on the map"""
        # Find the location in coordinates DataFrame
        location = self.coordinates[self.coordinates['Location'] == location_name]
        if not location.empty:
            # Get the coordinates
            x, y = location.iloc[0]['X'], location.iloc[0]['Y']
            
            # Clear previous robot marker
            self.map_canvas.delete("robot_marker")
            
            # Place a new marker on the map
            self.map_canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5, 
                fill="red", outline="black", tags="robot_marker"
            )
            
            # Update the current location label
            self.current_loc_var.set(location_name)
            
            self.log_message(f"Robot position updated to {location_name}")
    
    def select_nearest_locations(self, template_size):
        """Select only nearest locations for calculating the Euclidean distance"""
        if not self.matched_location:
            return self.ref_data  # Return all data if no matched location
        
        # Find the matched location coordinates
        matched_data = self.distances[self.distances['Location'] == self.matched_location]
        if matched_data.empty:
            return self.ref_data
        
        matched_location_x = matched_data.iloc[0]['X']
        matched_location_y = matched_data.iloc[0]['Y']
        
        # Filter locations based on distance
        selected_locations = self.distances[
            (self.distances['X'] >= matched_location_x - template_size) & 
            (self.distances['X'] <= matched_location_x + template_size) & 
            (self.distances['Y'] >= matched_location_y - template_size) & 
            (self.distances['Y'] <= matched_location_y + template_size)
        ]
        
        # Filter reference data based on selected locations
        filtered_data = self.ref_data[self.ref_data['Location'].isin(selected_locations['Location'])]
        return filtered_data
    
    def find_closest_location(self, real_time_data, filtered_data):
        """Compute Euclidean distance to find closest location"""
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
    
    def read_serial_data(self):
        """Read data from the serial port in a separate thread"""
        while not self.stop_thread:
            try:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    
                    # Skip empty lines
                    if not data:
                        continue
                    
                    # Try to parse the data as comma-separated values
                    try:
                        values = [float(val) for val in data.split(',') if val.strip()]
                        
                        # Check if we have enough data to process
                        if len(values) >= 3:  # We need at least 3 values (M_X, M_Y, M_Z)
                            # Use only the first three values as X, Y, Z
                            self.vector = values[:3]
                            
                            # Add to history
                            self.history.append(self.vector.copy())
                            if len(self.history) > self.max_history:
                                self.history.pop(0)
                            
                            # Update displayed values
                            self.x_var.set(f"{self.vector[0]:.2f}")
                            self.y_var.set(f"{self.vector[1]:.2f}")
                            self.z_var.set(f"{self.vector[2]:.2f}")
                            
                            # Calculate magnitude
                            magnitude = np.sqrt(sum(x*x for x in self.vector))
                            self.mag_var.set(f"{magnitude:.2f}")
                            
                            # Process location data if we have set locations
                            if hasattr(self, 'Starting_location') and hasattr(self, 'Target_location'):
                                # Select only nearest locations for calculate the Euclidean distance
                                template_size = 1
                                filtered_data = self.select_nearest_locations(template_size)
                                
                                # Find the closest location
                                closest_location = self.find_closest_location(self.vector, filtered_data)
                                self.matched_location = closest_location
                                
                                # Check if the robot has reached the target location
                                target_location_name = self.Target_location.iloc[0]['Location']
                                
                                if closest_location == target_location_name:
                                    self.log_message(f"Robot has reached the target location: {closest_location}")
                                    # Send data using serial port
                                    if self.serial_port and self.serial_port.is_open:
                                        command_to_send = "5"
                                        self.serial_port.write(command_to_send.encode('utf-8'))
                                        self.log_message(f"Sent command: {command_to_send}")
                                        self.serial_port.write("\n".encode('utf-8'))
                                
                                # Check if the location has changed
                                if closest_location != self.previous_location:
                                    self.log_message(f"The robot is at: {closest_location}")
                                    self.update_robot_position(closest_location)
                                    self.previous_location = closest_location
                            
                    except ValueError as e:
                        self.log_message(f"Error parsing data: {str(e)}")
                        
            except Exception as e:
                self.log_message(f"Serial error: {str(e)}")
                time.sleep(0.5)  # Wait before trying again
                
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    
    def update_vector_plot(self):
        """Update the 3D vector plot with current data"""
        if not hasattr(self, 'ax'):
            return
            
        # Clear the plot
        self.ax.clear()
        
        # Draw coordinate axes and setup
        self.draw_coordinate_axes()
        self.ax.set_xlabel('X (μT)')
        self.ax.set_ylabel('Y (μT)')
        self.ax.set_zlabel('Z (μT)')
        self.ax.set_title('Real-time Magnetic Vector Visualization')
        
        # Auto-adjust scale if enabled
        if self.auto_scale_var.get() and self.vector is not None:
            max_val = max(abs(self.vector[0]), abs(self.vector[1]), abs(self.vector[2]), 50)
            self.ax.set_xlim([-max_val*1.2, max_val*1.2])
            self.ax.set_ylim([-max_val*1.2, max_val*1.2])
            self.ax.set_zlim([-max_val*1.2, max_val*1.2])
        else:
            # Default limits
            self.ax.set_xlim([-100, 100])
            self.ax.set_ylim([-100, 100])
            self.ax.set_zlim([-100, 100])
        
        # Draw grid
        self.ax.grid(True)
        
        # Draw the current vector
        if self.vector is not None:
            x, y, z = self.vector
            self.ax.quiver(0, 0, 0, x, y, z, color='purple', arrow_length_ratio=0.1, linewidth=2)
            
            # Label the vector endpoint
            self.ax.text(x*1.1, y*1.1, z*1.1, f"({x:.1f}, {y:.1f}, {z:.1f})", 
                         color='purple', fontsize=9)
            
            # Draw projections if enabled
            if self.show_proj_var.get():
                # XY plane projection (z=0)
                self.ax.plot([0, x], [0, y], [0, 0], 'b--', alpha=0.5)
                self.ax.scatter(x, y, 0, color='blue', alpha=0.7)
                
                # XZ plane projection (y=0)
                self.ax.plot([0, x], [0, 0], [0, z], 'g--', alpha=0.5)
                self.ax.scatter(x, 0, z, color='green', alpha=0.7)
                
                # YZ plane projection (x=0)
                self.ax.plot([0, 0], [0, y], [0, z], 'r--', alpha=0.5)
                self.ax.scatter(0, y, z, color='red', alpha=0.7)
                
                # Draw dashed lines from vector point to projections
                self.ax.plot([x, x], [y, y], [z, 0], 'k:', alpha=0.3)
                self.ax.plot([x, x], [y, 0], [z, z], 'k:', alpha=0.3)
                self.ax.plot([x, 0], [y, y], [z, z], 'k:', alpha=0.3)
        
        # Draw vector history if enabled
        if self.show_history_var.get() and self.history:
            history_array = np.array(self.history)
            self.ax.plot(history_array[:, 0], history_array[:, 1], history_array[:, 2], 'c-', alpha=0.5)
        
        # Redraw the canvas
        self.canvas.draw()
    
    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # Scroll to the end
    
    def on_closing(self):
        """Handle window closing event"""
        if self.is_connected:
            self.toggle_connection()  # Disconnect if connected
        self.root.destroy()

def main():
    root = tk.Tk()
    app = CombinedLocationVisualization(root)
    root.mainloop()

if __name__ == "__main__":
    main()