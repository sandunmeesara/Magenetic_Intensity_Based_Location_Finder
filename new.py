import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import serial
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MagneticVectorVisualization:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-time Magnetic Vector Visualization")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize vector components with default values
        self.vector = [0, 0, 0]
        self.history = []  # Store historical data
        self.max_history = 100  # Maximum number of historical points
        
        # Serial connection parameters
        self.serial_port = None
        self.is_connected = False
        self.stop_thread = False
        self.serial_thread = None
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left frame for controls
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create right frame for visualization
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Setup the visualization plot
        self.setup_plot()
        
        # Setup the controls
        self.setup_controls()
        
        # Initial plot update
        self.update_plot()
    
    def setup_plot(self):
        """Configure the 3D plot for vector visualization"""
        # Create figure and 3D axis
        self.fig = plt.Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set axis labels
        self.ax.set_xlabel('X (μT)')
        self.ax.set_ylabel('Y (μT)')
        self.ax.set_zlabel('Z (μT)')
        
        # Set plot title
        self.ax.set_title('Real-time Magnetic Vector Visualization')
        
        # Set axis limits with some padding
        self.ax.set_xlim([-100, 100])
        self.ax.set_ylim([-100, 100])
        self.ax.set_zlim([-100, 100])
        
        # Draw grid
        self.ax.grid(True)
        
        # Draw coordinate axes
        self.draw_coordinate_axes()
        
        # Embed the plot in the tkinter window
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add a toolbar
        toolbar_frame = ttk.Frame(self.right_frame)
        toolbar_frame.pack(fill=tk.X)
        
    def draw_coordinate_axes(self):
        """Draw the coordinate axes"""
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
    
    def setup_controls(self):
        """Setup UI controls for serial connection and settings"""
        # Serial Connection Frame
        conn_frame = ttk.LabelFrame(self.left_frame, text="Serial Connection")
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # COM Port selection
        ttk.Label(conn_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM10")  # Default port
        self.port_entry = ttk.Entry(conn_frame, width=10, textvariable=self.port_var)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Baud Rate selection
        ttk.Label(conn_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.IntVar(value=9600)  # Default baud rate
        baud_options = [9600, 19200, 38400, 57600, 115200]
        self.baud_combo = ttk.Combobox(conn_frame, width=8, textvariable=self.baud_var, values=baud_options)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Connect/Disconnect button
        self.conn_button = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.conn_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Vector Information Frame
        info_frame = ttk.LabelFrame(self.left_frame, text="Vector Information")
        info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # X component display
        ttk.Label(info_frame, text="X:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.x_var = tk.StringVar(value="0.00")
        ttk.Label(info_frame, textvariable=self.x_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Y component display
        ttk.Label(info_frame, text="Y:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.y_var = tk.StringVar(value="0.00")
        ttk.Label(info_frame, textvariable=self.y_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Z component display
        ttk.Label(info_frame, text="Z:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.z_var = tk.StringVar(value="0.00")
        ttk.Label(info_frame, textvariable=self.z_var).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Magnitude display
        ttk.Label(info_frame, text="Magnitude:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.mag_var = tk.StringVar(value="0.00")
        ttk.Label(info_frame, textvariable=self.mag_var).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Log Frame
        log_frame = ttk.LabelFrame(self.left_frame, text="Data Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log text area
        self.log_text = tk.Text(log_frame, height=10, width=25)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Clear log button
        self.clear_button = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(fill=tk.X, padx=5, pady=5)
        
        # Visualization options frame
        viz_frame = ttk.LabelFrame(self.left_frame, text="Visualization Options")
        viz_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Show history checkbox
        self.show_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(viz_frame, text="Show History", variable=self.show_history_var, 
                       command=self.update_plot).pack(padx=5, pady=5, anchor=tk.W)
        
        # Show projections checkbox
        self.show_proj_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(viz_frame, text="Show Projections", variable=self.show_proj_var, 
                       command=self.update_plot).pack(padx=5, pady=5, anchor=tk.W)
        
        # Auto-adjust scale checkbox
        self.auto_scale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(viz_frame, text="Auto-adjust Scale", variable=self.auto_scale_var, 
                       command=self.update_plot).pack(padx=5, pady=5, anchor=tk.W)
    
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
                        
                        # Check if we have at least the X, Y, Z components
                        if len(values) >= 3:
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
                            
                            # Log the data periodically (e.g., every 10th reading)
                            if len(self.history) % 10 == 0:
                                self.log_message(f"X: {self.vector[0]:.2f}, Y: {self.vector[1]:.2f}, Z: {self.vector[2]:.2f}")
                                
                    except ValueError as e:
                        self.log_message(f"Error parsing data: {str(e)}")
                        
            except Exception as e:
                self.log_message(f"Serial error: {str(e)}")
                time.sleep(0.5)  # Wait before trying again
                
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    
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
        self.update_plot()
        return []
    
    def update_plot(self):
        """Update the plot with current vector data"""
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
    
    def clear_log(self):
        """Clear the log text area"""
        self.log_text.delete(1.0, tk.END)
    
    def on_closing(self):
        """Handle window closing event"""
        if self.is_connected:
            self.toggle_connection()  # Disconnect if connected
        self.root.destroy()

def main():
    root = tk.Tk()
    app = MagneticVectorVisualization(root)
    root.mainloop()

if __name__ == "__main__":
    main()