"""
Audio visualization widget with embedded matplotlib canvas.
Pure display responsibility - receives plotting data and shows graphs.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class AudioVisualizationWidget(QWidget):
    """Widget for displaying audio analysis graphs with embedded matplotlib."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Create matplotlib canvas
        self.figure = Figure(figsize=(10, 4), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        
        # Add canvas to layout
        layout.addWidget(self.canvas)
        
        # Status label for feedback
        self.status_label = QLabel("Ready for audio analysis...")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Initialize with empty plot
        self._create_empty_plot()
        
    def _create_empty_plot(self):
        """Creates an empty placeholder plot."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Drop an audio file to see analysis', 
                ha='center', va='center', transform=ax.transAxes,
                fontsize=14, alpha=0.7)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw()
    
    def display_analysis_figure(self, figure):
        """
        Display a matplotlib figure in the widget.
        
        Args:
            figure: matplotlib.figure.Figure to display
        """
        # Clear current figure
        self.figure.clear()
        
        # Copy the provided figure to our canvas
        # Get the subplot from the provided figure
        source_ax = figure.get_axes()[0]
        
        # Create new subplot in our figure
        ax = self.figure.add_subplot(111)
        
        # Copy all the plot elements
        for child in source_ax.get_children():
            if hasattr(child, 'get_data'):
                # Copy line plots
                try:
                    x_data, y_data = child.get_data()
                    ax.plot(x_data, y_data, color=child.get_color(), 
                           linewidth=child.get_linewidth())
                except:
                    pass
        
        # Copy collections (fill_between creates PolyCollection)
        for collection in source_ax.collections:
            ax.add_collection(collection)
        
        # Copy axis properties
        ax.set_xlim(source_ax.get_xlim())
        ax.set_ylim(source_ax.get_ylim())
        ax.set_xlabel(source_ax.get_xlabel())
        ax.set_ylabel(source_ax.get_ylabel())
        ax.set_title(source_ax.get_title())
        
        # Copy colorbar if it exists
        if hasattr(figure, '_colorbar') or len(figure.get_axes()) > 1:
            # Try to copy colorbar
            try:
                cbar = figure.colorbar(source_ax.collections[-1], ax=ax, label='RMS Power')
            except:
                pass
        
        self.figure.tight_layout()
        self.canvas.draw()
        self.status_label.setText("Analysis complete - displaying power graph")
    
    def display_figure_direct(self, figure):
        """
        Display a figure by replacing our canvas figure entirely.
        More reliable than copying elements.
        
        Args:
            figure: matplotlib.figure.Figure to display
        """
        # Remove old canvas
        layout = self.layout()
        layout.removeWidget(self.canvas)
        self.canvas.deleteLater()
        
        # Create new canvas with the provided figure
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        layout.insertWidget(0, self.canvas)  # Insert at position 0 (before status label)
        
        self.canvas.draw()
        self.status_label.setText("Analysis complete - displaying power graph")
    
    def set_status(self, message):
        """Update the status label."""
        self.status_label.setText(message)