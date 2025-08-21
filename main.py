import sys
import os
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QSplitter, QLabel, QListWidget, 
                            QTextEdit, QListWidgetItem, QPushButton, QFileDialog)
from PyQt5.QtCore import Qt

from audio_visualization_widget import AudioVisualizationWidget
from analysis_results_manager import AnalysisResultsManager
from logger_setup import setup_logging, parse_log_args
from font_manager import initialize_fonts, get_font_manager
from font_control_widget import FontControlWidget


class MainWindow(QMainWindow):
    """Main application window with modular audio analysis interface."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
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
        
        # Open File button
        self.open_file_button = QPushButton("Open Audio File...")
        self.open_file_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.open_file_button)
        
        # Font control cluster
        self.font_control = FontControlWidget()
        self.font_control.fontChanged.connect(self.on_font_changed)
        self.font_control.fontSizeChanged.connect(self.on_font_size_changed)
        self.font_control.plotRefreshRequested.connect(self.on_plot_refresh_requested)
        layout.addWidget(self.font_control)
        
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
        self.analysis_manager.progressUpdate.connect(self.on_progress_update)
    
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
        
        self.logger.info(f"Files dropped: {len(files)} total, {len(audio_files)} audio files")
        
        if audio_files:
            # Analyze the first audio file
            # TODO: Add support for multiple file queue
            file_path = audio_files[0]
            self.logger.info(f"Starting analysis of dropped file: {os.path.basename(file_path)}")
            self.analysis_manager.analyze_file(file_path)
        else:
            self.visualization_widget.set_status("No audio files detected in drop")
            self.logger.warning("No supported audio files found in drop")
    
    def open_file_dialog(self):
        """Open file dialog to select audio files for analysis."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",  # Default directory (empty = current directory)
            "Audio Files (*.mp3 *.wav *.flac);;All Files (*)"
        )
        
        if file_path:  # User selected a file (didn't cancel)
            self.logger.info(f"File selected via dialog: {os.path.basename(file_path)}")
            self.analysis_manager.analyze_file(file_path)
    
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
        self.logger.error(f"Analysis failed for {filename}: {error_message}")
        self.visualization_widget.set_status(f"Error analyzing {filename}: {error_message}")
    
    def on_progress_update(self, message, percentage):
        """Called when analysis progress updates."""
        self.logger.debug(f"Progress: {message} ({percentage}%)")
        self.visualization_widget.set_status(f"{message} ({percentage}%)")
    
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
    
    def on_font_changed(self, font_name: str, font_type: str):
        """Called when font selection changes."""
        self.logger.info(f"Font changed via GUI: {font_name} ({font_type})")
        # Auto-regenerate current plot with new font
        self._regenerate_current_plot()
    
    def on_font_size_changed(self, font_size: int):
        """Called when Qt font size changes."""
        self.logger.info(f"Qt font size changed via GUI: {font_size}pt")
        # Qt font size doesn't affect matplotlib plots, so no regeneration needed
    
    def on_plot_refresh_requested(self):
        """Called when manual plot refresh is requested."""
        self.logger.info("Manual plot refresh requested via GUI")
        self._regenerate_current_plot()
    
    def _regenerate_current_plot(self):
        """Regenerate the current plot with updated font settings."""
        try:
            # Get the currently selected file
            current_item = self.file_list.currentItem()
            if not current_item:
                self.logger.debug("No file selected for plot regeneration")
                return
            
            file_path = current_item.data(Qt.UserRole)
            if not file_path:
                self.logger.debug("No file path found for current selection")
                return
            
            self.logger.info(f"Regenerating plot for: {os.path.basename(file_path)}")
            
            # Re-analyze the file to regenerate plots with new font
            self.analysis_manager.analyze_file(file_path)
            
        except Exception as e:
            self.logger.error(f"Error regenerating plot: {e}")
            self.visualization_widget.set_status(f"Error regenerating plot: {e}")


if __name__ == '__main__':
    # Parse logging arguments before creating QApplication
    log_level, log_to_file = parse_log_args()
    
    # Initialize logging
    logger = setup_logging(log_level, log_to_file)
    logger.info("Starting Audio Mastering Analysis Toolkit")
    logger.info(f"Command line args: log-level={log_level}, log-file={log_to_file}")
    
    app = QApplication(sys.argv)
    
    # Initialize font system before creating any widgets
    font_success = initialize_fonts()
    if font_success:
        logger.info("Font system initialized successfully")
        # Log font status for debugging
        font_status = get_font_manager().get_status_report()
        logger.debug(f"Font status: matplotlib={font_status['matplotlib_configured']}, "
                    f"qt={font_status['qt_configured']}, "
                    f"custom_fonts={font_status['custom_fonts_loaded']}")
    else:
        logger.warning("Font system initialization failed - CJK characters may not display properly")
    
    # Set application style
    app.setStyle('Fusion')  # Modern cross-platform style
    logger.debug("Application style set to Fusion")
    
    window = MainWindow()
    window.show()
    logger.info("GUI window displayed")
    
    sys.exit(app.exec_())