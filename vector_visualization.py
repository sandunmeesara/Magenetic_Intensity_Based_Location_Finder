import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, CheckButtons
from mpl_toolkits.mplot3d import Axes3D

class VectorVisualization:
    def __init__(self):
        # Initialize vector components
        self.x = 3
        self.y = 2
        self.z = 4
        
        # Create the figure and 3D axis
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Setup the plot
        self.setup_plot()
        
        # Add UI controls
        self.add_controls()
        
        # Render initial vector
        self.update_plot()
    
    def setup_plot(self):
        """Configure the 3D plot appearance"""
        # Set axis labels
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        
        # Set plot title
        self.ax.set_title('3D Vector Visualization')
        
        # Set axis limits with some padding
        limit = 10
        self.ax.set_xlim([-limit, limit])
        self.ax.set_ylim([-limit, limit])
        self.ax.set_zlim([-limit, limit])
        
        # Draw grid
        self.ax.grid(True)
        
        # Draw coordinate axes
        self.draw_coordinate_axes()
    
    def draw_coordinate_axes(self):
        """Draw the coordinate axes"""
        # X-axis in red
        self.ax.plot([0, 10], [0, 0], [0, 0], color='red', linewidth=2)
        # Y-axis in green
        self.ax.plot([0, 0], [0, 10], [0, 0], color='green', linewidth=2)
        # Z-axis in blue
        self.ax.plot([0, 0], [0, 0], [0, 10], color='blue', linewidth=2)
        
        # Label the axes
        self.ax.text(10.5, 0, 0, "X", color='red', fontsize=12)
        self.ax.text(0, 10.5, 0, "Y", color='green', fontsize=12)
        self.ax.text(0, 0, 10.5, "Z", color='blue', fontsize=12)
    
    def add_controls(self):
        """Add text input boxes for vector components"""
        # Adjust the plot to make room for controls
        self.fig.subplots_adjust(bottom=0.3)
        
        # Create text box axes
        ax_x = plt.axes([0.2, 0.2, 0.1, 0.05])
        ax_y = plt.axes([0.45, 0.2, 0.1, 0.05])
        ax_z = plt.axes([0.7, 0.2, 0.1, 0.05])
        
        # Create text boxes for each component
        self.text_x = TextBox(ax_x, 'X:', initial=str(self.x))
        self.text_y = TextBox(ax_y, 'Y:', initial=str(self.y))
        self.text_z = TextBox(ax_z, 'Z:', initial=str(self.z))
        
        # Set text box callbacks
        self.text_x.on_submit(self.update_x)
        self.text_y.on_submit(self.update_y)
        self.text_z.on_submit(self.update_z)
        
        # Add check button for projections
        ax_check = plt.axes([0.35, 0.1, 0.3, 0.1])
        self.check = CheckButtons(ax_check, ['Show Projections'], [True])
        self.check.on_clicked(self.toggle_projections)
        
        # Add vector info text
        self.info_text = self.fig.text(0.5, 0.02, self.get_vector_info(), 
                                       ha='center', fontsize=10)
    
    def update_x(self, value):
        """Update the x component and redraw"""
        try:
            self.x = float(value)
            self.update_plot()
        except ValueError:
            pass  # Invalid input, ignore
    
    def update_y(self, value):
        """Update the y component and redraw"""
        try:
            self.y = float(value)
            self.update_plot()
        except ValueError:
            pass  # Invalid input, ignore
    
    def update_z(self, value):
        """Update the z component and redraw"""
        try:
            self.z = float(value)
            self.update_plot()
        except ValueError:
            pass  # Invalid input, ignore
    
    def toggle_projections(self, label):
        """Toggle projection visibility"""
        self.update_plot()
    
    def get_vector_info(self):
        """Generate vector information text"""
        magnitude = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        return f"Vector: ({self.x}, {self.y}, {self.z})    Magnitude: {magnitude:.2f}"
    
    def update_plot(self):
        """Update the plot with the current vector"""
        # Clear the current plot
        self.ax.clear()
        
        # Reset the plot configuration
        self.setup_plot()
        
        # Draw the vector
        self.ax.quiver(0, 0, 0, self.x, self.y, self.z, 
                       color='purple', arrow_length_ratio=0.1, linewidth=2)
        
        # Update vector info text
        self.info_text.set_text(self.get_vector_info())
        
        # Draw projections if enabled
        if self.check.get_status()[0]:
            self.draw_projections()
        
        # Refresh the plot
        self.fig.canvas.draw_idle()
    
    def draw_projections(self):
        """Draw projections on the coordinate planes"""
        # XY plane projection (z=0)
        self.ax.plot([0, self.x], [0, self.y], [0, 0], 'b--', alpha=0.5)
        self.ax.scatter(self.x, self.y, 0, color='blue', alpha=0.7)
        
        # XZ plane projection (y=0)
        self.ax.plot([0, self.x], [0, 0], [0, self.z], 'g--', alpha=0.5)
        self.ax.scatter(self.x, 0, self.z, color='green', alpha=0.7)
        
        # YZ plane projection (x=0)
        self.ax.plot([0, 0], [0, self.y], [0, self.z], 'r--', alpha=0.5)
        self.ax.scatter(0, self.y, self.z, color='red', alpha=0.7)
        
        # Draw dashed lines from vector point to projections
        self.ax.plot([self.x, self.x], [self.y, self.y], [self.z, 0], 'k:', alpha=0.3)
        self.ax.plot([self.x, self.x], [self.y, 0], [self.z, self.z], 'k:', alpha=0.3)
        self.ax.plot([self.x, 0], [self.y, self.y], [self.z, self.z], 'k:', alpha=0.3)

    def show(self):
        """Display the plot"""
        plt.show()


if __name__ == "__main__":
    # Create and show the visualization
    viz = VectorVisualization()
    viz.show()