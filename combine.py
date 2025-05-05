import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
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
        self.root.title("Magnetic Vector Visualization & Control")
        
        # Set a fixed minimum size to prevent controls from disappearing
        self.root.geometry("1000x900")
        self.root.minsize(1000, 800)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure styles for large buttons
        style = ttk.Style()
        style.configure("Big.TButton", font=('TkDefaultFont', 11, 'bold'), padding=5)
        
        # Initialize global variables
        self.matched_location = ''
        self.previous_location = None
        self.vector = [0, 0, 0]
        self.history = []
        self.max_history = 100
        
        # Serial connection parameters
        self.serial_port = None
        self.is_connected = False
        self.stop_thread = False
        self.serial_thread = None
        
        # Initialize the log_text as a None value
        self.log_text = None
        
        # Load data
        self.load_data()
        
        # Create main container with GRID layout for more control
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.main_container.columnconfigure(0, weight=1)
        
        # Configure row weights to ensure proper distribution
        self.main_container.rowconfigure(0, weight=1)  # Top part expands
        self.main_container.rowconfigure(1, weight=0, minsize=200)  # Bottom part has fixed minimum size
        
        # Create top frame for vector visualization
        self.top_frame = ttk.Frame(self.main_container)
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create bottom frame for controls with FIXED HEIGHT to ensure visibility
        self.bottom_frame = ttk.LabelFrame(self.main_container, text="Control Panel")
        self.bottom_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Setup control panel FIRST to initialize log_text
        self.setup_control_panel()
        
        # Setup vector visualization
        self.setup_vector_panel()
        
        # Create separate window for map
        self.create_map_window()
        
        # Initial plot update
        self.update_vector_plot()
        
        # Force the window to update
        self.root.update_idletasks()
    
    def create_map_window(self):
        """Create a separate window for the map visualization"""
        self.map_window = Toplevel(self.root)
        self.map_window.title("Robot Location Map")
        # Start with a reasonable size, will be adjusted when map loads
        self.map_window.geometry("1000x900")  
        self.map_window.protocol("WM_DELETE_WINDOW", self.on_map_window_close)
        self.map_window.minsize(800, 600)
        
        # Create a frame for the map
        self.map_frame = ttk.Frame(self.map_window)
        self.map_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Set up the map visualization
        self.setup_map_panel()
        
        # Status panel at the bottom of map window
        self.map_status_frame = ttk.Frame(self.map_window)
        self.map_status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Show all locations button
        ttk.Button(self.map_status_frame, text="Show All Locations", 
                  command=self.show_all_locations).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Current location display
        ttk.Label(self.map_status_frame, text="Current Location:").pack(side=tk.LEFT, padx=(20, 5), pady=5)
        self.current_loc_var = tk.StringVar(value="Not set")
        ttk.Label(self.map_status_frame, textvariable=self.current_loc_var, 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5, pady=5)
    
    def on_map_window_close(self):
        """Handle the map window closing without closing the main application"""
        self.log_message("Map window closed. You can reopen it from the 'View' menu.")
        self.map_window.withdraw()  # Hide instead of destroy
    
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
        """Set up the map visualization panel showing full-size map with scrollbars"""
        self.map_inner_frame = ttk.Frame(self.map_frame)
        self.map_inner_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        try:
            # Load the map image
            self.map_image = Image.open("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map.png")
            
            # Get the original dimensions
            original_width, original_height = self.map_image.width, self.map_image.height
            
            # Create the photo image without resizing
            self.map_photo = ImageTk.PhotoImage(self.map_image)
            
            # Create a frame for scrollbars
            scroll_frame = ttk.Frame(self.map_inner_frame)
            scroll_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add scrollbars
            h_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.HORIZONTAL)
            v_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL)
            
            # Create canvas with fixed size
            screen_width = self.map_window.winfo_screenwidth() * 0.8  # 80% of screen width
            screen_height = self.map_window.winfo_screenheight() * 0.8  # 80% of screen height
            
            # Create canvas with scrollbars
            self.map_canvas = tk.Canvas(
                scroll_frame,
                width=min(original_width, screen_width),
                height=min(original_height, screen_height),
                xscrollcommand=h_scrollbar.set,
                yscrollcommand=v_scrollbar.set
            )
            
            # Configure scrollbars
            h_scrollbar.config(command=self.map_canvas.xview)
            v_scrollbar.config(command=self.map_canvas.yview)
            
            # Pack everything
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.map_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Add the image to the canvas
            self.map_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
            
            # Set the scroll region to the size of the image
            self.map_canvas.config(scrollregion=(0, 0, original_width, original_height))
            
            # Add a prominent instruction label
            instruction_label = ttk.Label(
                self.map_inner_frame, 
                text="Use scrollbars to navigate the map if needed", 
                font=('TkDefaultFont', 10, 'italic'),
                foreground='blue'
            )
            instruction_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
            
            self.log_message(f"Map loaded at full size: {original_width}x{original_height}")
        except Exception as e:
            self.log_message(f"Error loading map: {str(e)}")
            self.map_canvas = tk.Canvas(self.map_inner_frame, width=800, height=600, bg='lightgray')
            self.map_canvas.pack(fill=tk.BOTH, expand=True)
            self.map_canvas.create_text(400, 300, text="Map image not found or could not be loaded", 
                                      font=('Arial', 14, 'bold'), fill='red')
    
    def setup_vector_panel(self):
        """Set up the 3D vector visualization panel in the main window"""
        # Create a labeled frame for vector visualization
        self.vector_frame = ttk.LabelFrame(self.top_frame, text="Magnetic Vector Visualization")
        self.vector_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create figure and 3D axis
        self.fig = plt.Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set axis labels and title
        self.ax.set_xlabel('X (μT)')
        self.ax.set_ylabel('Y (μT)')
        self.ax.set_zlabel('Z (μT)')
        self.ax.set_title('Real-time Magnetic Vector Visualization')
        
        # Set initial axis limits
        self.ax.set_xlim([-100, 100])
        self.ax.set_ylim([-100, 100])
        self.ax.set_zlim([-100, 100])
        
        # Draw grid
        self.ax.grid(True)
        
        # Draw coordinate axes
        self.draw_coordinate_axes()
        
        # Embed plot in tkinter window
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.vector_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create vector information panel
        self.vector_info_frame = ttk.LabelFrame(self.top_frame, text="Vector Information")
        self.vector_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Grid for vector components
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
        """Set up the bottom control panel in the main window with guaranteed visibility"""
        # Clear anything that might already be in the bottom frame
        for widget in self.bottom_frame.winfo_children():
            widget.destroy()
        
        # Make the panel stand out with strong border
        self.bottom_frame.configure(borderwidth=3, relief="raised")
        
        # Use grid layout manager instead of pack for more precise control
        self.bottom_frame.columnconfigure(0, weight=1)
        self.bottom_frame.columnconfigure(1, weight=1)
        
        # Serial connection frame - position on the left
        self.conn_frame = ttk.LabelFrame(self.bottom_frame, text="Serial Connection")
        self.conn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # COM Port selection
        ttk.Label(self.conn_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM10")
        self.port_entry = ttk.Entry(self.conn_frame, width=10, textvariable=self.port_var)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Baud Rate selection
        ttk.Label(self.conn_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.IntVar(value=9600)
        baud_options = [9600, 19200, 38400, 57600, 115200]
        self.baud_combo = ttk.Combobox(self.conn_frame, width=8, textvariable=self.baud_var, values=baud_options)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Connect/Disconnect button - MAKE VISIBLY LARGER
        style = ttk.Style()
        style.configure("Big.TButton", font=('TkDefaultFont', 11, 'bold'), padding=5)
        self.conn_button = ttk.Button(self.conn_frame, text="Connect", command=self.toggle_connection,
                                     style="Big.TButton")
        self.conn_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Location settings frame - position on the right
        self.location_frame = ttk.LabelFrame(self.bottom_frame, text="Location Settings")
        self.location_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Starting location input
        ttk.Label(self.location_frame, text="Starting Location:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_loc_var = tk.StringVar()
        self.start_loc_entry = ttk.Entry(self.location_frame, width=10, textvariable=self.start_loc_var, 
                                       font=('TkDefaultFont', 10))
        self.start_loc_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Target location input
        ttk.Label(self.location_frame, text="Target Location:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.target_loc_var = tk.StringVar()
        self.target_loc_entry = ttk.Entry(self.location_frame, width=10, textvariable=self.target_loc_var,
                                        font=('TkDefaultFont', 10))
        self.target_loc_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Set locations button - MAKE VISIBLY LARGER
        self.set_locations_button = ttk.Button(self.location_frame, text="Set Locations", 
                                             command=self.set_locations,
                                             style="Big.TButton")
        self.set_locations_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Log frame - NEW ROW spanning both columns for consistent display
        self.log_frame = ttk.LabelFrame(self.bottom_frame, text="System Log")
        self.log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # Configure row weights to ensure log frame gets proper space
        self.bottom_frame.rowconfigure(0, weight=0)  # Control row doesn't expand
        self.bottom_frame.rowconfigure(1, weight=1)  # Log row expands to fill space
        
        # Text widget for logs
        self.log_text = tk.Text(self.log_frame, height=5, width=80)
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=5)
        
        # Initial log messages
        self.log_message("Application started. Please follow these steps:")
        self.log_message("1. Connect to the serial port")
        self.log_message("2. Enter starting and target location numbers")
        self.log_message("3. Click 'Set Locations' to initialize navigation")
    
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
            # Get user input for locations
            starting_loc_num = self.start_loc_var.get().strip()
            target_loc_num = self.target_loc_var.get().strip()
            
            # Log the input values for debugging
            self.log_message(f"Input received - Starting: '{starting_loc_num}', Target: '{target_loc_num}'")
            
            # Validate input
            if not starting_loc_num or not target_loc_num:
                messagebox.showerror("Input Error", "Please enter both starting and target location numbers.")
                return
            
            # Format location names
            self.matched_location = f"data_location_{starting_loc_num}"
            start_location = f"data_location_{starting_loc_num}"
            target_location = f"data_location_{target_loc_num}"
            
            # Get starting location data
            starting_location_data = self.distances[self.distances['Location'] == start_location]
            if starting_location_data.empty:
                messagebox.showerror("Location Error", f"Starting location {start_location} not found in data.")
                return
            x1, y1 = starting_location_data.iloc[0]['X'], starting_location_data.iloc[0]['Y']

            # Get target location data
            target_location_data = self.distances[self.distances['Location'] == target_location]
            if target_location_data.empty:
                messagebox.showerror("Location Error", f"Target location {target_location} not found in data.")
                return
            x2, y2 = target_location_data.iloc[0]['X'], target_location_data.iloc[0]['Y']
            
            # Store location data
            self.Starting_location = starting_location_data
            self.Target_location = target_location_data
            
            # Log the selected locations
            self.log_message(f"Starting location set to: {start_location}")
            self.log_message(f"Target location set to: {target_location}")
            
            # Calculate angle for navigation
            angle_degrees = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angle_degrees = angle_degrees if angle_degrees >= 0 else 360 + angle_degrees
            self.log_message(f"Angle to turn: {angle_degrees:.2f} degrees")
            
            # Calculate angle in radians
            angle_degrees = angle_degrees if angle_degrees >= 0 else 360 + angle_degrees
            self.log_message(f"Angle to turn: {angle_degrees:.2f} degrees")
            
            # Calculate angle in radians
            angle = np.arctan2(y2 - y1, x2 - x1)
            angle = angle if angle >= 0 else 2 * np.pi + angle
            
            # Send command via serial port if connected
            if self.is_connected and self.serial_port and self.serial_port.is_open:
                command_to_send = f"t{angle}"
                self.serial_port.write(command_to_send.encode('utf-8'))
                self.log_message(f"Sent command: {command_to_send}")
            else:
                self.log_message("Serial port not connected. Cannot send command.")
            
            # Bring map window to front if it exists
            if hasattr(self, 'map_window'):
                self.map_window.lift()
                self.map_window.focus_force()
            else:
                self.create_map_window()
            
            # Update the map with markers
            self.update_map(starting_location_data, target_location_data)
            
        except Exception as e:
            messagebox.showerror("Set Locations Error", f"Error setting locations: {str(e)}")
    
    def update_map(self, starting_location, target_location):
        """Update the map with markers for starting and target locations"""
        try:
            # Clear previous markers
            self.map_canvas.delete("location_marker")
            
            # Get the starting and target location names
            start_name = starting_location.iloc[0]['Location']
            target_name = target_location.iloc[0]['Location']
            
            # First, look up coordinates in coordinates dataframe
            start_coord = self.coordinates[self.coordinates['Location'] == start_name]
            target_coord = self.coordinates[self.coordinates['Location'] == target_name]
            
            # Use coordinates dataframe if available, otherwise use distances dataframe
            if not start_coord.empty:
                x1, y1 = start_coord.iloc[0]['X'], start_coord.iloc[0]['Y']
            else:
                x1, y1 = starting_location.iloc[0]['X'], starting_location.iloc[0]['Y']
                self.log_message(f"Warning: Using fallback coordinates for {start_name}")
            
            if not target_coord.empty:
                x2, y2 = target_coord.iloc[0]['X'], target_coord.iloc[0]['Y']
            else:
                x2, y2 = target_location.iloc[0]['X'], target_location.iloc[0]['Y']
                self.log_message(f"Warning: Using fallback coordinates for {target_name}")
            
            # Debug information
            self.log_message(f"Start coordinates: ({x1}, {y1})")
            self.log_message(f"Target coordinates: ({x2}, {y2})")
            
            # Draw starting location marker (blue)
            self.map_canvas.create_oval(
                x1 - 10, y1 - 10, x1 + 10, y1 + 10, 
                fill="blue", outline="black", width=2, tags="location_marker"
            )
            self.map_canvas.create_text(
                x1, y1 - 20, text=f"Start ({start_name.split('_')[-1]})", 
                fill="blue", font=("Arial", 10, "bold"), tags="location_marker"
            )
            
            # Draw target location marker (green)
            self.map_canvas.create_oval(
                x2 - 10, y2 - 10, x2 + 10, y2 + 10, 
                fill="green", outline="black", width=2, tags="location_marker"
            )
            self.map_canvas.create_text(
                x2, y2 - 20, text=f"Target ({target_name.split('_')[-1]})", 
                fill="green", font=("Arial", 10, "bold"), tags="location_marker"
            )
            
            # Draw a line between start and target with distance label
            self.map_canvas.create_line(
                x1, y1, x2, y2, fill="gray", dash=(4, 2), width=2, 
                arrow=tk.LAST, tags="location_marker"
            )
            
            # Calculate distance and angle
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            angle_degrees = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angle_degrees = angle_degrees if angle_degrees >= 0 else 360 + angle_degrees
            
            # Calculate midpoint for the distance label
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Create background rectangle for distance label
            text_bg = self.map_canvas.create_rectangle(
                mid_x - 60, mid_y - 25, mid_x + 60, mid_y, 
                fill="white", outline="lightgray", tags="location_marker"
            )
            
            # Add distance and angle label
            self.map_canvas.create_text(
                mid_x, mid_y - 10, 
                text=f"Distance: {distance:.1f} px\nAngle: {angle_degrees:.1f}°", 
                fill="darkblue", font=("Arial", 8), tags="location_marker"
            )
            
            # Add a legend
            legend_x = 10
            legend_y = self.map_image.height - 80
            
            self.map_canvas.create_rectangle(
                legend_x, legend_y, legend_x+150, legend_y+70, 
                fill="white", outline="black", tags="location_marker"
            )
            
            self.map_canvas.create_text(
                legend_x+75, legend_y+10, text="Legend", 
                font=("Arial", 10, "bold"), tags="location_marker"
            )
            
            # Legend items
            self.map_canvas.create_oval(legend_x+10, legend_y+25, legend_x+20, legend_y+35, 
                                       fill="blue", outline="black", tags="location_marker")
            self.map_canvas.create_text(legend_x+90, legend_y+30, text="Starting Location", 
                                      anchor=tk.W, font=("Arial", 8), tags="location_marker")
            
            self.map_canvas.create_oval(legend_x+10, legend_y+45, legend_x+20, legend_y+55, 
                                       fill="green", outline="black", tags="location_marker")
            self.map_canvas.create_text(legend_x+90, legend_y+50, text="Target Location", 
                                      anchor=tk.W, font=("Arial", 8), tags="location_marker")
        
        except Exception as e:
            self.log_message(f"Error updating map: {str(e)}")
            messagebox.showerror("Map Error", f"Failed to update map: {str(e)}")
    
    def read_serial_data(self):
        """Read data from the serial port in a separate thread"""
        while not self.stop_thread:
            try:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting > 0:
                    # Add this line to read the data from serial port
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
                                # Select only nearest locations for distance calculation
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
        
        # Check if log_text exists before using it
        if self.log_text is not None:
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)  # Scroll to the end
        else:
            # Fall back to print if log_text is not available
            print(f"[{timestamp}] {message}")
    
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
    
    def show_all_locations(self):
        """Show all available locations on the map"""
        try:
            # Clear any previous markers
            self.map_canvas.delete("all_locations")
            
            # Display the map image again
            self.map_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
            
            # Draw all locations from the coordinates dataframe
            location_count = 0
            
            # Get unique locations only
            unique_locations = self.coordinates.drop_duplicates(subset=['Location'])
            
            for idx, row in unique_locations.iterrows():
                location_name = row['Location']
                x, y = row['X'], row['Y']
                
                # Verify coordinates are within canvas bounds
                if 0 <= x < self.map_image.width and 0 <= y < self.map_image.height:
                    # Draw the location point
                    self.map_canvas.create_oval(
                        x-5, y-5, x+5, y+5, 
                        fill="orange", outline="black", tags="all_locations"
                    )
                    
                    # Extract location number for cleaner display
                    loc_num = location_name.split('_')[-1] if '_' in location_name else location_name
                    
                    # Add the location label
                    self.map_canvas.create_text(
                        x, y-10, text=loc_num, 
                        font=("Arial", 8), fill="black", tags="all_locations"
                    )
                    
                    location_count += 1
            
            # Add a legend
            legend_x = 10
            legend_y = self.map_image.height - 60
            
            self.map_canvas.create_rectangle(
                legend_x, legend_y, legend_x+120, legend_y+50, 
                fill="white", outline="black", tags="all_locations"
            )
            
            self.map_canvas.create_text(
                legend_x+60, legend_y+10, text="Legend", 
                font=("Arial", 10, "bold"), tags="all_locations"
            )
            
            # Legend items
            self.map_canvas.create_oval(legend_x+10, legend_y+25, legend_x+20, legend_y+35, 
                                       fill="orange", outline="black", tags="all_locations")
            self.map_canvas.create_text(legend_x+70, legend_y+30, text="Location point", 
                                      anchor=tk.W, font=("Arial", 8), tags="all_locations")
            
            self.log_message(f"Displayed {location_count} locations on the map")
            
        except Exception as e:
            self.log_message(f"Error showing locations: {str(e)}")
            messagebox.showerror("Map Error", f"Failed to show locations: {str(e)}")

    def update_robot_position(self, location_name):
        """Update the robot's position on the map"""
        try:
            # Find the location in coordinates DataFrame
            location = self.coordinates[self.coordinates['Location'] == location_name]
            if not location.empty:
                # Get the coordinates
                x, y = location.iloc[0]['X'], location.iloc[0]['Y']
                
                # Clear previous robot marker
                self.map_canvas.delete("robot_marker")
                
                # Make the robot marker more visible and animated
                # Outer circle (pulsing effect)
                self.map_canvas.create_oval(
                    x - 15, y - 15, x + 15, y + 15,
                    outline="red", width=2, tags="robot_marker"
                )
                
                # Inner circle (solid)
                self.map_canvas.create_oval(
                    x - 8, y - 8, x + 8, y + 8, 
                    fill="red", outline="black", width=2, tags="robot_marker"
                )
                
                # Add label with location number
                loc_num = location_name.split('_')[-1] if '_' in location_name else location_name
                self.map_canvas.create_text(
                    x, y - 25, text=f"ROBOT ({loc_num})", 
                    fill="red", font=("Arial", 10, "bold"), tags="robot_marker"
                )
                
                # Update the current location label
                self.current_loc_var.set(location_name)
                
                self.log_message(f"Robot position updated to {location_name} at coordinates ({x}, {y})")
                
                # Make sure the map window is visible
                if hasattr(self, 'map_window') and not self.map_window.winfo_viewable():
                    self.map_window.deiconify()
                    self.map_window.lift()
            else:
                self.log_message(f"Warning: Could not find coordinates for location {location_name}")
        except Exception as e:
            self.log_message(f"Error updating robot position: {str(e)}")
    
    def on_closing(self):
        """Handle window closing event"""
        if self.is_connected:
            self.toggle_connection()  # Disconnect if connected
        
        # Close map window if it exists
        if hasattr(self, 'map_window') and self.map_window.winfo_exists():
            self.map_window.destroy()
            
        self.root.destroy()

def main():
    root = tk.Tk()
    app = CombinedLocationVisualization(root)
    root.mainloop()

if __name__ == "__main__":
    main()