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
import os  # Add this to your imports at the top

class CombinedLocationVisualization:
    def __init__(self, root):
        self.root = root
        self.root.title("Magnetic Vector Visualization & Control")
        
        # Set a fixed minimum size to prevent controls from disappearing
        self.root.geometry("1200x900")  # Make it even bigger to fit everything
        self.root.minsize(1100, 800)     # Increase minimum size
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure styles for large buttons
        style = ttk.Style()
        style.configure("Big.TButton", font=('TkDefaultFont', 11, 'bold'), padding=5)
        
        # Initialize global variables
        self.matched_location = ''
        self.previous_location = None
        self.vector = [0, 0, 0]
        self.history = []
        self.max_history = 100  # Fixed value, no longer adjustable
        
        # Initialize visualization control variables
        self.show_history_var = tk.BooleanVar(value=True)
        self.show_proj_var = tk.BooleanVar(value=True)
        self.auto_scale_var = tk.BooleanVar(value=True)
        
        # Serial connection parameters
        self.serial_port = None
        self.is_connected = False
        self.stop_thread = False
        self.serial_thread = None
        
        # Initialize the log_text as a None value
        self.log_text = None
        
        # Load data
        self.load_data()
        
        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure columns for side-by-side layout
        self.main_container.columnconfigure(0, weight=1)  # Left column (controls)
        self.main_container.columnconfigure(1, weight=2)  # Right column (visualization + log/template)
        
        # Configure rows
        self.main_container.rowconfigure(0, weight=1)  # Top row
        
        # Create left panel for controls
        self.left_panel = ttk.Frame(self.main_container)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create right master panel that will contain both vector viz and log/template
        self.right_master_panel = ttk.Frame(self.main_container)
        self.right_master_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Configure right master panel to have vector viz on top, and split panel below
        self.right_master_panel.rowconfigure(0, weight=3)  # Vector visualization (larger)
        self.right_master_panel.rowconfigure(1, weight=2)  # Bottom split panel (smaller)
        self.right_master_panel.columnconfigure(0, weight=1)  # Full width
        
        # Create panel for vector visualization on top
        self.right_panel = ttk.Frame(self.right_master_panel)
        self.right_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create bottom split panel for log and template
        self.bottom_split_panel = ttk.Frame(self.right_master_panel)
        self.bottom_split_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure bottom split panel to have system log on left and template on right
        self.bottom_split_panel.columnconfigure(0, weight=1)  # System log
        self.bottom_split_panel.columnconfigure(1, weight=1)  # Template settings
        self.bottom_split_panel.rowconfigure(0, weight=1)  # Full height
        
        # Create system log panel on left side of bottom split
        self.log_panel = ttk.LabelFrame(self.bottom_split_panel, text="System Log")
        self.log_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create template settings panel on right side of bottom split
        self.template_panel = ttk.LabelFrame(self.bottom_split_panel, text="Template Settings")
        self.template_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Configure left panel to stack controls vertically
        self.left_panel.rowconfigure(0, weight=0)  # Serial connection
        self.left_panel.rowconfigure(1, weight=0)  # Location settings
        self.left_panel.rowconfigure(2, weight=0)  # Map & Algorithm settings 
        self.left_panel.rowconfigure(3, weight=1)  # Extra space at the bottom
        self.left_panel.columnconfigure(0, weight=1)  # Full width
        
        # Setup log panel first to initialize log_text
        self.setup_log_panel()
        
        # Setup template settings in the template panel
        self.setup_template_panel()
        
        # Setup control panels on the left
        self.setup_left_control_panels()
        
        # Setup vector visualization on the right
        self.setup_vector_panel()
        
        # Create separate window for map
        self.create_map_window()
        
        # Initial plot update
        self.update_vector_plot()
        
        # Force the window to update
        self.root.update_idletasks()
        
        # Add these new variables for map and algorithm selection
        self.map_paths = {
            "Default Map": "e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map.png",
            "Blueprint Map": "e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map_blueprint.png",
            "Satellite Map": "e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map_satellite.png",
            "Schematic Map": "e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Map_Marker/map_schematic.png"
        }
        
        self.current_map = "Default Map"
        self.current_algorithm = "Euclidean Distance"
    
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
        """Set up the 3D vector visualization panel on the right side of the main window with a modern look"""
        # Create a vertical layout
        vector_main_frame = ttk.Frame(self.right_panel)
        vector_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure row weights to give more space to the plot
        vector_main_frame.rowconfigure(0, weight=4)  # Vector visualization (larger)
        vector_main_frame.rowconfigure(1, weight=0)  # Vector controls (fixed size)
        vector_main_frame.rowconfigure(2, weight=0)  # Vector info (fixed size)
        vector_main_frame.columnconfigure(0, weight=1)  # Full width
        
        # Create a labeled frame for vector visualization
        self.vector_frame = ttk.LabelFrame(vector_main_frame, text="Magnetic Vector Visualization")
        self.vector_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
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
        
        # Create control panel below the visualization with a modern look
        viz_options = ttk.LabelFrame(vector_main_frame, text="Visualization Controls")
        viz_options.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Add a modern look with a frame that uses ttk styling
        control_frame = ttk.Frame(viz_options, padding=(10, 10, 10, 10))
        control_frame.pack(fill=tk.X, expand=True)
        
        # Create a horizontal layout for controls
        controls_container = ttk.Frame(control_frame)
        controls_container.pack(fill=tk.X, expand=True)
        
        # Set fixed height with fixed packing
        controls_container.config(height=50)
        
        # Use a grid layout for better organization
        controls_container.columnconfigure(0, weight=1)
        controls_container.columnconfigure(1, weight=1)
        controls_container.columnconfigure(2, weight=1)
        controls_container.columnconfigure(3, weight=1)
        
        # History trace checkbox with standard styling
        history_check = ttk.Checkbutton(
            controls_container, 
            text="History Trace", 
            variable=self.show_history_var,
            command=self.update_vector_plot
        )
        history_check.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # XYZ projections checkbox
        proj_check = ttk.Checkbutton(
            controls_container, 
            text="XYZ Projections", 
            variable=self.show_proj_var,
            command=self.update_vector_plot
        )
        proj_check.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Auto-scale checkbox
        scale_check = ttk.Checkbutton(
            controls_container, 
            text="Auto-adjust Scale", 
            variable=self.auto_scale_var,
            command=self.update_vector_plot
        )
        scale_check.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Add refresh button with standard style
        refresh_btn = ttk.Button(
            controls_container, 
            text="Refresh Plot", 
            command=self.update_vector_plot
        )
        refresh_btn.grid(row=0, column=3, padx=10, pady=5, sticky="e")
        
        # Vector information panel below the controls
        self.vector_info_frame = ttk.LabelFrame(vector_main_frame, text="Vector Information")
        self.vector_info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Grid for vector components
        grid_frame = ttk.Frame(self.vector_info_frame)
        grid_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # X component display
        ttk.Label(grid_frame, text="X:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.x_var = tk.StringVar(value="0.00")
        ttk.Label(grid_frame, textvariable=self.x_var, font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Y component display
        ttk.Label(grid_frame, text="Y:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.y_var = tk.StringVar(value="0.00")
        ttk.Label(grid_frame, textvariable=self.y_var, font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Z component display
        ttk.Label(grid_frame, text="Z:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.z_var = tk.StringVar(value="0.00")
        ttk.Label(grid_frame, textvariable=self.z_var, font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # Magnitude display
        ttk.Label(grid_frame, text="Magnitude:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.mag_var = tk.StringVar(value="0.00")
        ttk.Label(grid_frame, textvariable=self.mag_var, font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
    
    def update_history_length(self, *args):
        """Update the maximum history length for vector visualization"""
        self.max_history = self.history_length_var.get()
        
        # Truncate history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        self.log_message(f"History length set to: {self.max_history}")
        self.update_vector_plot()
    
    def setup_control_panel(self):
        """Set up the bottom control panel in the main window with guaranteed visibility"""
        # Clear anything that might already be in the bottom frame
        for widget in self.bottom_frame.winfo_children():
            widget.destroy()
        
        # Make the panel stand out with strong border
        self.bottom_frame.configure(borderwidth=3, relief="raised")
        
        # Use grid layout manager with 3 columns
        self.bottom_frame.columnconfigure(0, weight=1)
        self.bottom_frame.columnconfigure(1, weight=1)
        self.bottom_frame.columnconfigure(2, weight=1)
        
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
        
        # Connect/Disconnect button
        style = ttk.Style()
        style.configure("Big.TButton", font=('TkDefaultFont', 11, 'bold'), padding=5)
        self.conn_button = ttk.Button(self.conn_frame, text="Connect", command=self.toggle_connection,
                                     style="Big.TButton")
        self.conn_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Location settings frame - position in the middle
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
        
        # Set locations button
        self.set_locations_button = ttk.Button(self.location_frame, text="Set Locations", 
                                             command=self.set_locations,
                                             style="Big.TButton")
        self.set_locations_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Template & Algorithm Settings frame on the right
        self.settings_frame = ttk.LabelFrame(self.bottom_frame, text="Template & Algorithm Settings")
        self.settings_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        # Use a notebook with tabs for better organization
        settings_notebook = ttk.Notebook(self.settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Map & Algorithm Settings
        map_algo_tab = ttk.Frame(settings_notebook)
        settings_notebook.add(map_algo_tab, text="Map & Algorithm")
        
        # Map selection
        ttk.Label(map_algo_tab, text="Select Map:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Map options
        self.map_var = tk.StringVar(value="Default Map")
        self.map_options = ["Default Map", "Blueprint Map", "Satellite Map", "Schematic Map"]
        self.map_combo = ttk.Combobox(map_algo_tab, width=15, 
                                    textvariable=self.map_var, 
                                    values=self.map_options)
        self.map_combo.grid(row=0, column=1, padx=5, pady=5)
        self.map_combo.bind("<<ComboboxSelected>>", self.change_map)
        
        # Algorithm selection
        ttk.Label(map_algo_tab, text="Location Algorithm:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Algorithm options
        self.algo_var = tk.StringVar(value="Euclidean Distance")
        self.algo_options = ["Euclidean Distance", "Manhattan Distance", "Weighted Average", "KNN (K=3)"]
        self.algo_combo = ttk.Combobox(map_algo_tab, width=15, 
                                    textvariable=self.algo_var, 
                                    values=self.algo_options)
        self.algo_combo.grid(row=1, column=1, padx=5, pady=5)
        self.algo_combo.bind("<<ComboboxSelected>>", self.change_algorithm)
        
        # Apply settings button
        self.apply_settings_button = ttk.Button(map_algo_tab, text="Apply Settings", 
                                             command=self.apply_map_algo_settings,
                                             style="Big.TButton")
        self.apply_settings_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Tab 2: Template Settings - FIXED LAYOUT WITH GRID ONLY
        template_tab = ttk.Frame(settings_notebook, padding=(10, 10, 10, 10))
        settings_notebook.add(template_tab, text="Template Settings")

        # Use a grid layout for the entire tab
        template_tab.columnconfigure(0, weight=1)
        template_tab.rowconfigure(0, weight=0)  # Size control row
        template_tab.rowconfigure(1, weight=0)  # Match display row
        template_tab.rowconfigure(2, weight=1)  # Info frame row
        template_tab.rowconfigure(3, weight=0)  # Button row - IMPORTANT

        # Template size label and spinner - GRID LAYOUT
        size_frame = ttk.Frame(template_tab)
        size_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        size_frame.columnconfigure(0, weight=1)
        size_frame.columnconfigure(1, weight=1)

        ttk.Label(size_frame, text="Template Size:").grid(row=0, column=0, sticky="w")
        self.template_size_var = tk.IntVar(value=5)
        template_spinner = ttk.Spinbox(
            size_frame, 
            from_=1, 
            to=20, 
            textvariable=self.template_size_var,
            width=5,
            wrap=True,
            command=self.update_template_info
        )
        template_spinner.grid(row=0, column=1, sticky="e")

        # Matched location display - GRID LAYOUT
        match_frame = ttk.Frame(template_tab)
        match_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        match_frame.columnconfigure(0, weight=1)
        match_frame.columnconfigure(1, weight=1)

        ttk.Label(match_frame, text="Current Matched:").grid(row=0, column=0, sticky="w")
        self.matched_loc_display = ttk.Label(
            match_frame, 
            text="None yet", 
            font=('TkDefaultFont', 9, 'bold'),
            foreground='blue'
        )
        self.matched_loc_display.grid(row=0, column=1, sticky="e")

        # Template Info Text - GRID LAYOUT
        info_frame = ttk.LabelFrame(template_tab, text="Template Info")
        info_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)

        # Set a minimum height with grid_propagate
        info_frame.config(height=100)
        info_frame.grid_propagate(False)

        # Text container with grid layout
        self.template_info_text = tk.Text(info_frame, width=25, height=5, borderwidth=1, relief="solid")
        template_info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.template_info_text.yview)
        self.template_info_text.configure(yscrollcommand=template_info_scroll.set)

        self.template_info_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        template_info_scroll.grid(row=0, column=1, sticky="ns", padx=0, pady=5)

        # Button to show template on map - GRID LAYOUT WITH GUARANTEED VISIBILITY
        show_template_btn = ttk.Button(
            template_tab, 
            text="Show Template on Map", 
            command=self.apply_template_to_main_map,
            style="Accent.TButton"
        )
        show_template_btn.grid(row=3, column=0, sticky="ew", padx=5, pady=10)

        # Initialize the template info display
        self.update_template_info()
    
    def setup_log_panel(self):
        """Set up the log panel in the right split panel"""
        # Create a frame with padding
        log_container = ttk.Frame(self.log_panel, padding=(5, 5, 5, 5))
        log_container.pack(fill=tk.BOTH, expand=True)
        
        # Text widget for logs with a monospace font
        self.log_text = tk.Text(log_container, height=15, font=('Consolas', 9), bg='#f8f8f8')
        self.log_scroll = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add timestamp and info tag configurations
        self.log_text.tag_configure("timestamp", foreground="blue")
        self.log_text.tag_configure("info", foreground="green")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")
        
        # Initial log messages
        self.log_message("Application started. Please follow these steps:", level="info")
        self.log_message("1. Connect to the serial port")
        self.log_message("2. Enter starting and target location numbers")
        self.log_message("3. Select Map and Algorithm if needed")
        self.log_message("4. Click 'Set Locations' to initialize navigation")

    def setup_left_control_panels(self):
        """Set up the control panels on the left side of the main window with a modern look"""
        # Apply modern style
        self.configure_modern_style()
        
        # Serial connection frame with modern styling
        self.conn_frame = ttk.LabelFrame(self.left_panel, text="Serial Connection")
        self.conn_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Add inner padding for a more modern look
        conn_inner = ttk.Frame(self.conn_frame, padding=(10, 10, 10, 10))
        conn_inner.pack(fill=tk.BOTH, expand=True)
        
        # COM Port selection
        port_frame = ttk.Frame(conn_inner)
        port_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(port_frame, text="COM Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="COM10")
        self.port_entry = ttk.Entry(port_frame, width=10, textvariable=self.port_var)
        self.port_entry.pack(side=tk.RIGHT)
        
        # Baud Rate selection
        baud_frame = ttk.Frame(conn_inner)
        baud_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(baud_frame, text="Baud Rate:").pack(side=tk.LEFT)
        self.baud_var = tk.IntVar(value=9600)
        baud_options = [9600, 19200, 38400, 57600, 115200]
        self.baud_combo = ttk.Combobox(baud_frame, width=8, textvariable=self.baud_var, values=baud_options)
        self.baud_combo.pack(side=tk.RIGHT)
        
        # Connect/Disconnect button
        self.conn_button = ttk.Button(conn_inner, text="Connect", command=self.toggle_connection,
                                     style="Accent.TButton")
        self.conn_button.pack(fill=tk.X, padx=5, pady=10)
        
        # Location settings frame
        self.location_frame = ttk.LabelFrame(self.left_panel, text="Location Settings")
        self.location_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Add inner padding
        loc_inner = ttk.Frame(self.location_frame, padding=(10, 10, 10, 10))
        loc_inner.pack(fill=tk.BOTH, expand=True)
        
        # Starting location input
        start_frame = ttk.Frame(loc_inner)
        start_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(start_frame, text="Starting Location:").pack(side=tk.LEFT)
        self.start_loc_var = tk.StringVar()
        self.start_loc_entry = ttk.Entry(start_frame, width=10, textvariable=self.start_loc_var)
        self.start_loc_entry.pack(side=tk.RIGHT)
        
        # Target location input
        target_frame = ttk.Frame(loc_inner)
        target_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(target_frame, text="Target Location:").pack(side=tk.LEFT)
        self.target_loc_var = tk.StringVar()
        # Create the target_loc_entry attribute before using it
        self.target_loc_entry = ttk.Entry(target_frame, width=10, textvariable=self.target_loc_var)
        self.target_loc_entry.pack(side=tk.RIGHT)
        
        # Set locations button
        self.set_locations_button = ttk.Button(loc_inner, text="Set Locations", 
                                             command=self.set_locations,
                                             style="Accent.TButton")
        self.set_locations_button.pack(fill=tk.X, padx=5, pady=10)
        
        # Map & Algorithm Settings frame - NOW SEPARATE FROM TEMPLATE
        self.map_algo_frame = ttk.LabelFrame(self.left_panel, text="Map & Algorithm Settings")
        self.map_algo_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        # Add inner padding
        map_algo_inner = ttk.Frame(self.map_algo_frame, padding=(10, 10, 10, 10))
        map_algo_inner.pack(fill=tk.BOTH, expand=True)
        
        # Map selection
        map_frame = ttk.Frame(map_algo_inner)
        map_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(map_frame, text="Select Map:").pack(side=tk.LEFT)
        
        # Map options
        self.map_var = tk.StringVar(value="Default Map")
        self.map_options = ["Default Map", "Blueprint Map", "Satellite Map", "Schematic Map"]
        self.map_combo = ttk.Combobox(map_frame, width=15, 
                                    textvariable=self.map_var, 
                                    values=self.map_options)
        self.map_combo.pack(side=tk.RIGHT)
        self.map_combo.bind("<<ComboboxSelected>>", self.change_map)
        
        # Algorithm selection
        algo_frame = ttk.Frame(map_algo_inner)
        algo_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(algo_frame, text="Location Algorithm:").pack(side=tk.LEFT)
        
        # Algorithm options
        self.algo_var = tk.StringVar(value="Euclidean Distance")
        self.algo_options = ["Euclidean Distance", "Manhattan Distance", "Weighted Average", "KNN (K=3)"]
        self.algo_combo = ttk.Combobox(algo_frame, width=15, 
                                    textvariable=self.algo_var, 
                                    values=self.algo_options)
        self.algo_combo.pack(side=tk.RIGHT)
        self.algo_combo.bind("<<ComboboxSelected>>", self.change_algorithm)
        
        # Apply settings button
        self.apply_settings_button = ttk.Button(map_algo_inner, text="Apply Settings", 
                                             command=self.apply_map_algo_settings,
                                             style="Accent.TButton")
        self.apply_settings_button.pack(fill=tk.X, padx=5, pady=10)
        
        # SEPARATE TEMPLATE SETTINGS - ENSURE FULL VISIBILITY
        self.template_frame = ttk.LabelFrame(self.left_panel, text="Template Settings")
        self.template_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        # Set a fixed minimum height to ensure visibility
        self.template_frame.configure(height=250)  # Increased height
        self.template_frame.grid_propagate(False)  # Prevent shrinking

        # Template settings inner frame with padding
        template_inner = ttk.Frame(self.template_frame, padding=(10, 10, 10, 10))
        template_inner.pack(fill=tk.BOTH, expand=True)

        # Use grid instead of pack for better control
        template_inner.columnconfigure(0, weight=1)
        template_inner.rowconfigure(0, weight=0)  # Size control
        template_inner.rowconfigure(1, weight=0)  # Match display
        template_inner.rowconfigure(2, weight=1)  # Template info (expandable)
        template_inner.rowconfigure(3, weight=0)  # Button (fixed)

        # Template size with spinbox
        size_frame = ttk.Frame(template_inner)
        size_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(size_frame, text="Template Size:").pack(side=tk.LEFT)
        self.template_size_var = tk.IntVar(value=5)
        template_spinner = ttk.Spinbox(
            size_frame, 
            from_=1, 
            to=20, 
            textvariable=self.template_size_var,
            width=5,
            wrap=True,
            command=self.update_template_info
        )
        template_spinner.pack(side=tk.RIGHT)

        # Matched location display
        match_frame = ttk.Frame(template_inner)
        match_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(match_frame, text="Current Matched:").pack(side=tk.LEFT)
        self.matched_loc_display = ttk.Label(
            match_frame, 
            text="None yet", 
            font=('TkDefaultFont', 9, 'bold'),
            foreground='blue'
        )
        self.matched_loc_display.pack(side=tk.RIGHT)

        # Template Info Text - USE GRID WITH FIXED HEIGHT
        info_frame = ttk.LabelFrame(template_inner, text="Template Info")
        info_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)

        # Make sure the text area has a minimum height
        self.template_info_text = tk.Text(info_frame, height=5, width=25, borderwidth=1, relief="solid")
        template_info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.template_info_text.yview)
        self.template_info_text.configure(yscrollcommand=template_info_scroll.set)

        self.template_info_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        template_info_scroll.grid(row=0, column=1, sticky="ns", padx=0, pady=5)

        # Show Template button - ENSURE VISIBILITY WITH GRID
        show_template_btn = ttk.Button(
            template_inner, 
            text="Show Template on Map", 
            command=self.apply_template_to_main_map,
            style="Accent.TButton"
        )
        show_template_btn.grid(row=3, column=0, sticky="ew", padx=5, pady=10)

        # Initialize the template info display
        self.update_template_info()
        
        # Configure left panel's row weights to allow for proper stretching
        self.left_panel.rowconfigure(4, weight=1)  # Extra row at the end to push everything up

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
        """Read data from the serial port in a separate thread with improved error handling"""
        while not self.stop_thread:
            try:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting > 0:
                    # Read data from serial port
                    data = self.serial_port.readline().decode('utf-8').strip()
                    
                    # Skip empty lines
                    if not data:
                        continue
                    
                    # Log raw data for debugging (optional - uncomment if needed)
                    # self.log_message(f"Raw data: {data}")
                    
                    # Try to parse the data as comma-separated values
                    try:
                        # Clean up the data: replace multiple commas with a single comma
                        # and ensure proper separation of numbers
                        cleaned_data = data
                        
                        # Handle case where values are run together without commas (e.g., '50.050.09')
                        # This regex looks for patterns like digit.digit.digit and adds a comma
                        import re
                        cleaned_data = re.sub(r'(\d+\.\d+)(\d+\.\d+)', r'\1,\2', cleaned_data)
                        
                        # Split by comma and filter out any empty parts
                        parts = [part.strip() for part in cleaned_data.split(',') if part.strip()]
                        
                        # Extract valid float values
                        values = []
                        for part in parts:
                            try:
                                # Try to convert to float
                                values.append(float(part))
                            except ValueError:
                                # If part contains multiple numbers without separator, try to split
                                if '.' in part:
                                    # Count number of decimal points
                                    decimal_count = part.count('.')
                                    if (decimal_count > 1):
                                        # This might be multiple values stuck together
                                        # Split at each decimal point after the first
                                        decimal_positions = [pos for pos, char in enumerate(part) if char == '.']
                                        
                                        # Process first number (up to the second decimal)
                                        if decimal_positions[0] > 0:
                                            first_num_end = decimal_positions[1]
                                            try:
                                                first_value = float(part[:first_num_end])
                                                values.append(first_value)
                                            except ValueError:
                                                pass
                                        
                                        # Process second number (from the second decimal)
                                        try:
                                            second_value = float(part[decimal_positions[1]-1:])
                                            values.append(second_value)
                                        except ValueError:
                                            pass
                        
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
                                # Find the closest matching location
                                filtered_data = self.select_nearest_locations(template_size=5)
                                closest_location = self.find_closest_location(self.vector, filtered_data)
                                
                                # Update the robot location on the map
                                if closest_location != self.previous_location:
                                    self.previous_location = closest_location
                                    self.update_robot_position(closest_location)
                    
                    except ValueError as e:
                        self.log_message(f"Error parsing data: {str(e)} in '{data}'")
                        # Continue processing even if one data point fails
                    
                    except Exception as e:
                        self.log_message(f"Unexpected error processing data: {str(e)}")
                        
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
    
    def log_message(self, message, level="normal"):
        """Add a styled message to the log with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        
        # Check if log_text exists before using it
        if self.log_text is not None:
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            
            # Apply different styling based on message level
            if level == "info":
                self.log_text.insert(tk.END, f"{message}\n", "info")
            elif level == "warning":
                self.log_text.insert(tk.END, f"{message}\n", "warning")
            elif level == "error":
                self.log_text.insert(tk.END, f"{message}\n", "error")
            else:
                self.log_text.insert(tk.END, f"{message}\n")
                
            self.log_text.see(tk.END)  # Scroll to the end
        else:
            # Fall back to print if log_text is not available
            print(f"[{timestamp}] {message}")
    
    def select_nearest_locations(self, template_size=None):
        """Select only nearest locations for calculating the Euclidean distance"""
        # If we have template locations from the template window, use those
        if hasattr(self, 'current_template_locations') and not self.current_template_locations.empty:
            # Filter reference data based on selected locations
            filtered_data = self.ref_data[self.ref_data['Location'].isin(self.current_template_locations['Location'])]
            size = self.template_size_var.get() if hasattr(self, 'template_size_var') else (template_size or 5)
            self.log_message(f"Using template settings window size: {size} with {len(filtered_data)} locations")
            return filtered_data
        
        # Otherwise, use the normal method
        # Use the value from the template settings window if available
        if hasattr(self, 'template_size_var'):
            template_size = self.template_size_var.get()
        else:
            # Use the provided value or default to 5
            template_size = template_size or 5
        
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
        
        # Log the template size being used
        self.log_message(f"Using template size: {template_size} with {len(filtered_data)} locations")
        
        return filtered_data
    
    def find_closest_location(self, real_time_data, filtered_data):
        """Compute distance to find closest location using the selected algorithm"""
        distances = []
        
        for index, row in filtered_data.iterrows():
            # Get reference data
            ref_data = [row['M_X'], row['M_Y'], row['M_Z']]
            
            # Calculate distance based on selected algorithm
            if self.current_algorithm == "Euclidean Distance":
                # Standard Euclidean distance
                distance = np.sqrt(
                    (real_time_data[0] - ref_data[0])**2 +
                    (real_time_data[1] - ref_data[1])**2 +
                    (real_time_data[2] - ref_data[2])**2
                )
            
            elif self.current_algorithm == "Manhattan Distance":
                # Manhattan (L1) distance
                distance = (
                    abs(real_time_data[0] - ref_data[0]) +
                    abs(real_time_data[1] - ref_data[1]) +
                    abs(real_time_data[2] - ref_data[2])
                )
            
            elif self.current_algorithm == "Weighted Average":
                # Weighted components (emphasize X and Y over Z)
                distance = np.sqrt(
                    1.5 * (real_time_data[0] - ref_data[0])**2 +
                    1.5 * (real_time_data[1] - ref_data[1])**2 +
                    0.7 * (real_time_data[2] - ref_data[2])**2
                )
            
            elif self.current_algorithm == "KNN (K=3)":
                # This will just calculate distances normally
                # The actual KNN logic happens after all distances are calculated
                distance = np.sqrt(
                    (real_time_data[0] - ref_data[0])**2 +
                    (real_time_data[1] - ref_data[1])**2 +
                    (real_time_data[2] - ref_data[2])**2
                )
            
            distances.append((row['Location'], distance))
        
        # Sort by smallest distance
        distances.sort(key=lambda x: x[1])
        
        # For KNN, return the most common location among the k=3 nearest neighbors
        if self.current_algorithm == "KNN (K=3)" and len(distances) >= 3:
            # Get the 3 closest locations
            closest_three = [loc for loc, _ in distances[:3]]
            # Count occurrences of each location
            from collections import Counter
            location_counts = Counter(closest_three)
            # Return the most common location
            return location_counts.most_common(1)[0][0]
        
        # For other algorithms, just return the closest location
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
                    
                # Update the matched location
                self.matched_location = location_name
                
                # Update the template info in the main window
                self.update_template_info()
                
                # If template is already shown on map, update it
                if self.map_canvas.find_withtag("template_viz"):
                    self.apply_template_to_main_map()
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
        
        # Close template window if it exists
        if hasattr(self, 'template_window') and self.template_window.winfo_exists():
            self.template_window.destroy()
        
        self.root.destroy()
    
    def change_map(self, event=None):
        """Handle map selection change"""
        selected_map = self.map_var.get()
        if (selected_map != self.current_map):
            self.current_map = selected_map
            self.log_message(f"Map changed to: {selected_map}")
            
            # The actual map will be loaded when Apply is clicked
            
    def change_algorithm(self, event=None):
        """Handle algorithm selection change"""
        selected_algo = self.algo_var.get()
        if (selected_algo != self.current_algorithm):
            self.current_algorithm = selected_algo
            self.log_message(f"Algorithm changed to: {selected_algo}")
            
            # The algorithm will be applied when Apply is clicked
    
    def apply_map_algo_settings(self):
        """Apply the selected map and algorithm settings"""
        try:
            # Apply map change
            map_path = self.map_paths.get(self.current_map)
            if not map_path or not os.path.exists(map_path):
                self.log_message(f"Warning: Map file not found at {map_path}")
                messagebox.showwarning("Map Not Found", 
                                      f"The selected map file was not found.\nUsing the current map instead.")
            else:
                # Reload the map in the map window
                self.reload_map(map_path)
                self.log_message(f"Successfully applied map: {self.current_map}")
            
            # Apply algorithm change - the algorithm will be used in find_closest_location
            self.log_message(f"Successfully applied algorithm: {self.current_algorithm}")
            
            # If locations are set, update the map
            if hasattr(self, 'Starting_location') and hasattr(self, 'Target_location'):
                self.update_map(self.Starting_location, self.Target_location)
                
        except Exception as e:
            self.log_message(f"Error applying settings: {str(e)}")
            messagebox.showerror("Settings Error", f"Failed to apply settings: {str(e)}")
    
    def reload_map(self, map_path):
        """Reload the map with a new image"""
        try:
            # Create new map image
            self.map_image = Image.open(map_path)
            original_width, original_height = self.map_image.width, self.map_image.height
            
            # Update the PhotoImage
            self.map_photo = ImageTk.PhotoImage(self.map_image)
            
            # Clear the canvas
            self.map_canvas.delete("all")
            
            # Add the new image
            self.map_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
            
            # Update the scroll region
            self.map_canvas.config(scrollregion=(0, 0, original_width, original_height))
            
            # If we had markers before, redraw them
            if hasattr(self, 'Starting_location') and hasattr(self, 'Target_location'):
                self.update_map(self.Starting_location, self.Target_location)
                
            self.log_message(f"Map reloaded with dimensions: {original_width}x{original_height}")
            
        except Exception as e:
            self.log_message(f"Error reloading map: {str(e)}")
            raise

    def open_template_settings(self):
        """Open a separate window for template size settings"""
        # Create a new Toplevel window if it doesn't exist or is closed
        if not hasattr(self, 'template_window') or not self.template_window.winfo_exists():
            self.template_window = Toplevel(self.root)
            self.template_window.title("Template Size Settings")
            self.template_window.geometry("700x500")
            self.template_window.minsize(600, 400)
            self.template_window.protocol("WM_DELETE_WINDOW", lambda: self.template_window.withdraw())
            
            # Main frame
            main_frame = ttk.Frame(self.template_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Controls frame at the top
            controls_frame = ttk.LabelFrame(main_frame, text="Template Size Control")
            controls_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Create a container for the slider
            slider_frame = ttk.Frame(controls_frame)
            slider_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Template size label
            ttk.Label(slider_frame, text="Template Size:").pack(side=tk.LEFT, padx=5)
            
            # Default template size
            self.template_size_var = tk.IntVar(value=5)
            
            # Template size slider - integers only
            template_scale = ttk.Scale(
                slider_frame,
                from_=1,
                to=20,
                variable=self.template_size_var,
                orient=tk.HORIZONTAL,
                length=300,
                command=lambda val: self._set_integer_template_size(val)
            )
            template_scale.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            # Value display
            value_label = ttk.Label(slider_frame, textvariable=self.template_size_var, width=3)
            value_label.pack(side=tk.LEFT, padx=5)
            
            # Apply to matched location section
            matched_frame = ttk.Frame(controls_frame)
            matched_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Current matched location display
            ttk.Label(matched_frame, text="Current Matched Location:").pack(side=tk.LEFT, padx=5)
            self.matched_loc_display = ttk.Label(matched_frame, text="None yet", font=('TkDefaultFont', 10, 'bold'))
            self.matched_loc_display.pack(side=tk.LEFT, padx=5)
            
            # Apply button, show on main map
            apply_btn = ttk.Button(
                matched_frame,
                text="Apply Template & Show on Main Map",
                command=self.apply_template_to_main_map,
                style="Big.TButton"
            )
            apply_btn.pack(side=tk.RIGHT, padx=10)
            
            # Results frame with tabbed interface
            results_notebook = ttk.Notebook(main_frame)
            results_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Tab 1: Text display of selected locations
            text_frame = ttk.Frame(results_notebook)
            results_notebook.add(text_frame, text="Selected Locations")
            
            # Add text widget for showing selected locations
            self.template_results_text = tk.Text(text_frame, height=15, width=60)
            text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.template_results_text.yview)
            self.template_results_text.configure(yscrollcommand=text_scroll.set)
            
            self.template_results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=5)
            
            # Tab 2: Map preview of template area
            map_frame = ttk.Frame(results_notebook)
            results_notebook.add(map_frame, text="Map Preview")
            
            # Create canvas for map preview
            self.template_canvas = tk.Canvas(map_frame, bg='white')
            self.template_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Initial update (only if we have a matched location)
            if hasattr(self, 'matched_location') and self.matched_location:
                self.update_template_preview_with_matched_location()
            else:
                # Display a placeholder
                self.template_results_text.insert(tk.END, "Waiting for a matched location...\n\n")
                self.template_results_text.insert(tk.END, "Connect to the serial port and set locations first.")
        else:
            # Just show the window if it already exists
            self.template_window.deiconify()
            self.template_window.lift()
            
            # Update matched location display
            if hasattr(self, 'matched_loc_display'):
                loc_text = self.matched_location if hasattr(self, 'matched_location') and self.matched_location else "None yet"
                self.matched_loc_display.config(text=loc_text)
                
            # Update preview if needed
            if hasattr(self, 'matched_location') and self.matched_location:
                self.update_template_preview_with_matched_location()

    def _set_integer_template_size(self, val):
        """Set template size to integer values only"""
        # Round to nearest integer
        int_val = round(float(val))
        self.template_size_var.set(int_val)
        
        # Update the preview
        if hasattr(self, 'matched_location') and self.matched_location:
            self.update_template_preview_with_matched_location()

    def update_template_preview_with_matched_location(self):
        """Update the template preview based on the current matched location"""
        try:
            # Use the currently matched location
            if not hasattr(self, 'matched_location') or not self.matched_location:
                self.template_results_text.delete('1.0', tk.END)
                self.template_results_text.insert(tk.END, "No matched location available yet.")
                return
                
            # Get the current template size
            template_size = self.template_size_var.get()
            
            # Clear previous results
            self.template_results_text.delete('1.0', tk.END)
            
            # Header information
            self.template_results_text.insert(tk.END, f"Template Size: {template_size}\n")
            self.template_results_text.insert(tk.END, f"Matched Location: {self.matched_location}\n\n")
            
            # Update matched location display
            if hasattr(self, 'matched_loc_display'):
                self.matched_loc_display.config(text=self.matched_location)
            
            # Find the matched location in the distances DataFrame
            matched_data = self.distances[self.distances['Location'] == self.matched_location]
            if matched_data.empty:
                self.template_results_text.insert(tk.END, f"Matched location '{self.matched_location}' not found in data.")
                return
            
            # Get matched location coordinates
            matched_x = matched_data.iloc[0]['X']
            matched_y = matched_data.iloc[0]['Y']
            
            # Calculate template bounds
            min_x = matched_x - template_size
            max_x = matched_x + template_size
            min_y = matched_y - template_size
            max_y = matched_y + template_size
            
            # Find locations within the template bounds
            template_locations = self.distances[
                (self.distances['X'] >= min_x) & 
                (self.distances['X'] <= max_x) & 
                (self.distances['Y'] >= min_y) & 
                (self.distances['Y'] <= max_y)
            ]
            
            # Show results in text view
            self.template_results_text.insert(tk.END, f"Number of locations in template: {len(template_locations)}\n")
            self.template_results_text.insert(tk.END, "Locations included in template:\n\n")
            
            # Format and display each location
            for idx, row in template_locations.iterrows():
                loc_name = row['Location']
                x, y = row['X'], row['Y']
                distance = np.sqrt((x - matched_x)**2 + (y - matched_y)**2)
                
                # Format entry with location name and distance
                entry = f"{loc_name} - Position: ({x}, {y}) - Distance from matched: {distance:.2f}\n"
                self.template_results_text.insert(tk.END, entry)
            
            # Store the template locations for use in find_closest_location
            self.current_template_locations = template_locations
            
            # Update the map preview
            self.draw_template_preview(matched_x, matched_y, template_size, template_locations)
            
        except Exception as e:
            self.template_results_text.delete('1.0', tk.END)
            self.template_results_text.insert(tk.END, f"Error updating template preview: {str(e)}")
            self.log_message(f"Template preview error: {str(e)}")

    def apply_template_to_main_map(self):
        """Apply the current template to the main map view"""
        try:
            if not hasattr(self, 'matched_location') or not self.matched_location:
                messagebox.showinfo("Template Error", "No matched location available yet.")
                return
                
            # Get the current template size
            template_size = self.template_size_var.get()
            
            # Find the matched location
            matched_data = self.distances[self.distances['Location'] == self.matched_location]
            if matched_data.empty:
                messagebox.showinfo("Template Error", f"Matched location '{self.matched_location}' not found in data.")
                return
            
            # Get matched location coordinates in the map coordinate system
            matched_coord = self.coordinates[self.coordinates['Location'] == self.matched_location]
            if matched_coord.empty:
                # Fall back to distance coordinates
                x, y = matched_data.iloc[0]['X'], matched_data.iloc[0]['Y']
                self.log_message(f"Warning: Using fallback coordinates for {self.matched_location}")
            else:
                x, y = matched_coord.iloc[0]['X'], matched_coord.iloc[0]['Y']
            
            # Clear any previous template visualizations
            self.map_canvas.delete("template_viz")
            
            # Draw template boundary on main map (rectangle)
            self.map_canvas.create_rectangle(
                x - template_size*10, y - template_size*10, 
                x + template_size*10, y + template_size*10,
                outline="blue", width=2, dash=(4, 2), tags="template_viz"
            )
            
            # Find locations within the template bounds
            # Convert template_size to a similar scale in the tile coordinates
            matched_tile_data = self.distances[self.distances['Location'] == self.matched_location]
            tile_x, tile_y = matched_tile_data.iloc[0]['X'], matched_tile_data.iloc[0]['Y']
            
            template_locations = self.distances[
                (self.distances['X'] >= tile_x - template_size) & 
                (self.distances['X'] <= tile_x + template_size) & 
                (self.distances['Y'] >= tile_y - template_size) & 
                (self.distances['Y'] <= tile_y + template_size)
            ]
            
            # Draw each location in the template
            for idx, row in template_locations.iterrows():
                loc_name = row['Location']
                
                # Get map coordinates for this location
                loc_coord = self.coordinates[self.coordinates['Location'] == loc_name]
                if not loc_coord.empty:
                    loc_x, loc_y = loc_coord.iloc[0]['X'], loc_coord.iloc[0]['Y']
                    
                    # Draw point for template location
                    self.map_canvas.create_oval(
                        loc_x-6, loc_y-6, loc_x+6, loc_y+6,
                        fill="cyan", outline="blue", tags="template_viz"
                    )
                    
                    # Draw small label
                    loc_num = loc_name.split('_')[-1] if '_' in loc_name else loc_name
                    self.map_canvas.create_text(
                        loc_x, loc_y-12, text=loc_num,
                        fill="blue", font=("Arial", 8), tags="template_viz"
                    )
            
            # Add a label for the template size
            self.map_canvas.create_text(
                x, y + template_size*10 + 15,
                text=f"Template Size: {template_size}",
                font=("Arial", 10, "bold"), fill="blue",
                tags="template_viz"
            )
            
            # Update the info message
            self.log_message(f"Template with size {template_size} displayed on main map")
            
        except Exception as e:
            self.log_message(f"Error applying template to main map: {str(e)}")
            messagebox.showerror("Template Error", f"Failed to apply template: {str(e)}")

    def draw_template_preview(self, matched_x, matched_y, template_size, template_locations):
        """Draw a preview of the template area on the canvas"""
        # Clear the canvas
        if hasattr(self, 'template_canvas'):
            self.template_canvas.delete("all")
        else:
            # If we don't need the map preview tab anymore, we can skip this
            return
        
        # Get canvas dimensions
        canvas_width = self.template_canvas.winfo_width()
        canvas_height = self.template_canvas.winfo_height()
        
        # Ensure canvas has size (it might not have been drawn yet)
        if (canvas_width < 10 or canvas_height < 10):
            canvas_width = 400
            canvas_height = 300
        
        # Calculate the scale and offset for drawing
        # Find min/max of locations for scaling
        all_x = template_locations['X'].tolist()
        all_y = template_locations['Y'].tolist()
        
        # Add the reference point and template bounds
        all_x.extend([matched_x - template_size - 5, matched_x + template_size + 5])
        all_y.extend([matched_y - template_size - 5, matched_y + template_size + 5])
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Calculate scaling factors
        padding = 30  # Padding around the edges
        width_scale = (canvas_width - 2 * padding) / (max_x - min_x) if max_x > min_x else 1
        height_scale = (canvas_height - 2 * padding) / (max_y - min_y) if max_y > min_y else 1
        scale = min(width_scale, height_scale)
        
        # Function to convert data coordinates to canvas coordinates
        def to_canvas(x, y):
            cx = padding + (x - min_x) * scale
            cy = padding + (y - min_y) * scale
            return cx, cy
        
        # Draw template boundary (rectangle)
        template_x1, template_y1 = to_canvas(matched_x - template_size, matched_y - template_size)
        template_x2, template_y2 = to_canvas(matched_x + template_size, matched_y + template_size)
        self.template_canvas.create_rectangle(
            template_x1, template_y1, template_x2, template_y2,
            outline="blue", width=2, dash=(4, 2)
        )
        
        # Draw all locations in the data set with faded appearance
        for idx, row in self.distances.iterrows():
            x, y = row['X'], row['Y']
            cx, cy = to_canvas(x, y)
            
            # Different color and size for points inside vs outside template
            if (x >= matched_x - template_size and x <= matched_x + template_size and
                y >= matched_y - template_size and y <= matched_y + template_size):
                # Inside template - highlight
                self.template_canvas.create_oval(
                    cx-5, cy-5, cx+5, cy+5,
                    fill="green", outline="black"
                )
            else:
                # Outside template - faded
                self.template_canvas.create_oval(
                    cx-3, cy-3, cx+3, cy+3,
                    fill="gray", outline="gray"
                )
        
        # Draw reference location (highlighted with star)
        ref_cx, ref_cy = to_canvas(matched_x, matched_y)
        
        # Draw a star for reference point
        star_size = 10
        points = [
            ref_cx, ref_cy - star_size,
            ref_cx + star_size/4, ref_cy - star_size/4,
            ref_cx + star_size, ref_cy - star_size/4,
            ref_cx + star_size/2, ref_cy + star_size/4,
            ref_cx + star_size*3/4, ref_cy + star_size,
            ref_cx, ref_cy + star_size*2/3,
            ref_cx - star_size*3/4, ref_cy + star_size,
            ref_cx - star_size/2, ref_cy + star_size/4,
            ref_cx - star_size, ref_cy - star_size/4,
            ref_cx - star_size/4, ref_cy - star_size/4,
        ]
        self.template_canvas.create_polygon(
            points, fill="red", outline="black"
        )

    def update_template_info(self, *args):
        """Update the template info display without opening a separate window"""
        try:
            # Get the current template size
            template_size = self.template_size_var.get()
            
            # Clear previous text
            if hasattr(self, 'template_info_text'):
                self.template_info_text.delete('1.0', tk.END)
            else:
                return
                
            # If no location is matched yet, show placeholder
            if not hasattr(self, 'matched_location') or not self.matched_location:
                self.template_info_text.insert(tk.END, "No matched location yet.\n\n")
                self.template_info_text.insert(tk.END, "Connect and set locations to see template info.")
                return
                
            # Update the matched location display
            if hasattr(self, 'matched_loc_display'):
                self.matched_loc_display.config(text=self.matched_location)
                
            # Find the matched location in the distances DataFrame
            matched_data = self.distances[self.distances['Location'] == self.matched_location]
            if matched_data.empty:
                self.template_info_text.insert(tk.END, f"Location '{self.matched_location}' not found.")
                return
                
            # Get matched location coordinates
            matched_x = matched_data.iloc[0]['X']
            matched_y = matched_data.iloc[0]['Y']
            
            # Calculate template bounds
            min_x = matched_x - template_size
            max_x = matched_x + template_size
            min_y = matched_y - template_size
            max_y = matched_y + template_size
            
            # Find locations within the template bounds
            template_locations = self.distances[
                (self.distances['X'] >= min_x) & 
                (self.distances['X'] <= max_x) & 
                (self.distances['Y'] >= min_y) & 
                (self.distances['Y'] <= max_y)
            ]
            
            # Store the template locations for use in find_closest_location
            self.current_template_locations = template_locations
            
            # Show info about the template
            self.template_info_text.insert(tk.END, f"Template size: {template_size}\n")
            self.template_info_text.insert(tk.END, f"Center: {self.matched_location}\n")
            self.template_info_text.insert(tk.END, f"Locations in template: {len(template_locations)}\n\n")
            
            # List the location names (shortened)
            self.template_info_text.insert(tk.END, "Included locations:\n")
            for idx, row in template_locations.iterrows():
                loc_name = row['Location']
                # Extract location number for cleaner display
                loc_num = loc_name.split('_')[-1] if '_' in loc_name else loc_name
                self.template_info_text.insert(tk.END, f"• {loc_num}\n")
                
        except Exception as e:
            if hasattr(self, 'template_info_text'):
                self.template_info_text.delete('1.0', tk.END)
                self.template_info_text.insert(tk.END, f"Error: {str(e)}")
            self.log_message(f"Template info error: {str(e)}")

    def configure_modern_style(self):
        """Configure modern styles for the application"""
        style = ttk.Style()
        
        # Check if we're using a theme that supports styling
        current_theme = style.theme_use()
        if current_theme not in ('vista', 'xpnative', 'clam'):
            # Try to use a modern theme if available
            try:
                style.theme_use('clam')  # clam is the most customizable built-in theme
            except:
                pass  # If theme doesn't exist, keep using current
        
        # Configure modern styles for buttons
        style.configure('TButton', padding=6)
        style.configure('Accent.TButton', font=('TkDefaultFont', 9, 'bold'), padding=8)
        
        # Configure modern styles for labels
        style.configure('TLabel', padding=2)
        
        # Configure modern styles for frames
        style.configure('TLabelframe', padding=5, borderwidth=2)
        style.configure('TLabelframe.Label', font=('TkDefaultFont', 9, 'bold'))
        
        # Configure modern styles for comboboxes and entries
        style.configure('TCombobox', padding=2)
        style.configure('TEntry', padding=2)
        
        # Configure modern styles for spinbox
        style.configure('TSpinbox', padding=2)
        
        # Configure notebook styles
        style.configure('TNotebook', padding=2)
        style.configure('TNotebook.Tab', padding=(10, 4), font=('TkDefaultFont', 9, 'bold'))

def main():
    root = tk.Tk()
    app = CombinedLocationVisualization(root)
    root.mainloop()

if __name__ == "__main__":  # <-- The '==' was missing
    main()