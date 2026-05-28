"""
Audio visualization widget with embedded matplotlib canvas.
Pure display responsibility - receives plotting data and shows graphs.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


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