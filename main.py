import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QSplitter, QLabel, QListWidget, 
                            QTextEdit, QListWidgetItem)
from PyQt5.QtCore import Qt

from audio_visualization_widget import AudioVisualizationWidget
from analysis_results_manager import AnalysisResultsManager


class MainWindow(QMainWindow):
    """Main application window with modular audio analysis interface."""
    
    def __init__(self):
        super().__init__()
        self.analysis_manager = AnalysisResultsManager()
        self.initUI()
        self.connect_signals()
    
    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle('Audio Mastering Analysis Toolkit')
        self.setGeometry(100, 100, 1200, 700)
        self.setAcceptDrops(True)
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - File list and metadata
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Visualization
        self.visualization_widget = AudioVisualizationWidget()
        splitter.addWidget(self.visualization_widget)
        
        # Set splitter proportions
        splitter.setSizes([300, 900])  # Left panel narrower than visualization
    
    def create_left_panel(self):
        """Create the left panel with file list and metadata."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File list
        self.file_list_label = QLabel("Analyzed Files:")
        layout.addWidget(self.file_list_label)
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        layout.addWidget(self.file_list)
        
        # Metadata display
        self.metadata_label = QLabel("File Information:")
        layout.addWidget(self.metadata_label)
        
        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)
        self.metadata_display.setMaximumHeight(150)
        layout.addWidget(self.metadata_display)
        
        # Instructions
        instructions = QLabel(
            "Drag and drop audio files (.mp3, .wav) onto this window to analyze them."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(instructions)
        
        return panel
    
    def connect_signals(self):
        """Connect analysis manager signals to GUI updates."""
        self.analysis_manager.analysisStarted.connect(self.on_analysis_started)
        self.analysis_manager.analysisCompleted.connect(self.on_analysis_completed)
        self.analysis_manager.analysisError.connect(self.on_analysis_error)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event for file drops."""
        if event.mimeData().hasUrls():
            # Check if any files have audio extensions
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp3', '.wav', '.flac')):
                    event.accept()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """Handle file drop event."""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        audio_files = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.flac'))]
        
        if audio_files:
            # Analyze the first audio file
            # TODO: Add support for multiple file queue
            file_path = audio_files[0]
            self.analysis_manager.analyze_file(file_path)
        else:
            self.visualization_widget.set_status("No audio files detected in drop")
    
    def on_analysis_started(self, file_path):
        """Called when analysis starts."""
        filename = os.path.basename(file_path)
        self.visualization_widget.set_status(f"Analyzing: {filename}...")
    
    def on_analysis_completed(self, file_path, result):
        """Called when analysis completes successfully."""
        filename = os.path.basename(file_path)
        
        # Add to file list if not already there
        existing_items = [self.file_list.item(i).text() 
                         for i in range(self.file_list.count())]
        if filename not in existing_items:
            item = QListWidgetItem(filename)
            item.setData(Qt.UserRole, file_path)  # Store full path
            self.file_list.addItem(item)
        
        # Get and display the analysis figure
        figure = self.analysis_manager.get_analysis_figure(file_path)
        if figure:
            self.visualization_widget.display_figure_direct(figure)
        
        # Update metadata display
        metadata_text = self.analysis_manager.get_metadata_text(file_path)
        self.metadata_display.setText(metadata_text)
        
        # Select the analyzed file in the list
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == file_path:
                self.file_list.setCurrentItem(item)
                break
    
    def on_analysis_error(self, file_path, error_message):
        """Called when analysis fails."""
        filename = os.path.basename(file_path)
        self.visualization_widget.set_status(f"Error analyzing {filename}: {error_message}")
    
    def on_file_selected(self, item):
        """Called when a file is selected from the list."""
        file_path = item.data(Qt.UserRole)
        
        # Display the analysis figure
        figure = self.analysis_manager.get_analysis_figure(file_path)
        if figure:
            self.visualization_widget.display_figure_direct(figure)
        
        # Update metadata display
        metadata_text = self.analysis_manager.get_metadata_text(file_path)
        self.metadata_display.setText(metadata_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')  # Modern cross-platform style
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())