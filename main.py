import sys
import os
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QSplitter, QLabel, QListWidget, 
                            QTextEdit, QListWidgetItem, QPushButton, QFileDialog)
from PyQt5.QtCore import Qt

from audio_visualization_widget import AudioVisualizationWidget, dataset_color
from analysis_results_manager import AnalysisResultsManager
from logger_setup import setup_logging, parse_log_args
from font_manager import initialize_fonts, get_font_manager
from font_control_widget import FontControlWidget
from plot_control_widget import PlotControlWidget
from ref_line_widget import RefLineControlWidget, RefLineDialog
from metrics import METRICS
from plotspec import RefLineProps, apply_x_mode


class MainWindow(QMainWindow):
    """Main application window with modular audio analysis interface."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.analysis_manager = AnalysisResultsManager()
        # Guards programmatic list mutations from triggering re-render storms.
        self._suppress_list_signals = False
        # Custom reference lines, owned here and pushed to the plot each render.
        self.ref_lines: list[RefLineProps] = []
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
        layout.addWidget(self.font_control)

        # Plot control cluster (metric selector + scale toggle + refresh)
        self.plot_control = PlotControlWidget()
        self.plot_control.metricChanged.connect(self.on_metric_changed)
        self.plot_control.viewChanged.connect(self.on_view_changed)
        self.plot_control.plotRefreshRequested.connect(self.on_plot_refresh_requested)
        layout.addWidget(self.plot_control)

        # Reference-line management cluster (list + add/edit/remove/clear).
        self.ref_line_control = RefLineControlWidget()
        self.ref_line_control.addRequested.connect(self.on_add_reference_line)
        self.ref_line_control.editRequested.connect(self.on_edit_reference_line)
        self.ref_line_control.removeRequested.connect(self.on_remove_reference_line)
        self.ref_line_control.clearRequested.connect(self.on_clear_reference_lines)
        layout.addWidget(self.ref_line_control)

        # File list. Each item carries a checkbox: the checked set is the overlay
        # set drawn on the graph; the highlighted item drives the metadata panel.
        self.file_list_label = QLabel("Analyzed Files (tick to overlay):")
        layout.addWidget(self.file_list_label)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        self.file_list.itemChanged.connect(self.on_file_check_changed)
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
        self.analysis_manager.metricComputeStarted.connect(self.on_metric_compute_started)
        self.analysis_manager.metricReady.connect(self.on_metric_ready)
        self.analysis_manager.metricComputeError.connect(self.on_metric_compute_error)
        self.visualization_widget.referenceLineMoved.connect(self.on_reference_line_moved)
    
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
            self.analysis_manager.analyze_file(file_path, self.plot_control.current_metric_id())
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
            self.analysis_manager.analyze_file(file_path, self.plot_control.current_metric_id())
    
    def on_analysis_started(self, file_path):
        """Called when analysis starts."""
        filename = os.path.basename(file_path)
        self.visualization_widget.set_status(f"Analyzing: {filename}...")
    
    def on_analysis_completed(self, file_path, result):
        """Called when analysis completes successfully."""
        filename = os.path.basename(file_path)

        # Add to file list (checked, so it joins the overlay set) if not present.
        item = self._item_for_path(file_path)
        if item is None:
            self._suppress_list_signals = True
            item = QListWidgetItem(filename)
            item.setData(Qt.UserRole, file_path)  # Store full path
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.file_list.addItem(item)
            self._suppress_list_signals = False

        # Update metadata display and highlight the analyzed file.
        self.metadata_display.setText(self.analysis_manager.get_metadata_text(file_path))
        self.file_list.setCurrentItem(item)

        # Redraw the overlay set for the current metric.
        self._refresh_view()
    
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
        """Called when a file is highlighted (drives the metadata panel only)."""
        file_path = item.data(Qt.UserRole)
        self.metadata_display.setText(self.analysis_manager.get_metadata_text(file_path))

    def on_file_check_changed(self, _item):
        """A checkbox toggled — the overlay set changed; redraw."""
        if self._suppress_list_signals:
            return
        self._refresh_view()

    def on_font_changed(self, font_name: str, font_type: str):
        """Called when font selection changes."""
        self.logger.info(f"Font changed via GUI: {font_name} ({font_type})")
        self._refresh_view()

    def on_font_size_changed(self, font_size: int):
        """Called when Qt font size changes."""
        self.logger.info(f"Qt font size changed via GUI: {font_size}pt")
        # Qt font size doesn't affect the plot axes fonts directly; no redraw needed.

    def on_metric_changed(self, metric_id: str):
        """Called when the metric selector changes."""
        self.logger.info(f"Metric changed via GUI: {metric_id}")
        # The value axis units change with the metric, so custom reference lines
        # placed against the old metric no longer mean anything — drop them.
        self.ref_lines.clear()
        self._sync_ref_lines()
        self._refresh_view()

    def on_add_reference_line(self):
        """Add a reference line at the current view centre, then edit it."""
        value = self.visualization_widget.current_view_center_y()
        props = RefLineProps(value=round(value, 2))
        self.ref_lines.append(props)
        self._sync_ref_lines()
        # Open the editor immediately so colour/tag/value can be set right away.
        self.on_edit_reference_line(len(self.ref_lines) - 1)

    def on_edit_reference_line(self, index: int):
        """Open the properties dialog for a reference line."""
        if not (0 <= index < len(self.ref_lines)):
            return
        dialog = RefLineDialog(self, self.ref_lines[index])
        if dialog.exec_():
            self.ref_lines[index] = dialog.result_props()
            self._sync_ref_lines()

    def on_remove_reference_line(self, index: int):
        """Delete a reference line."""
        if 0 <= index < len(self.ref_lines):
            del self.ref_lines[index]
            self._sync_ref_lines()

    def on_clear_reference_lines(self):
        """Remove all custom reference lines."""
        self.ref_lines.clear()
        self._sync_ref_lines()

    def on_reference_line_moved(self, index: int):
        """A line was dragged on the plot — its value is already updated; refresh list."""
        self.ref_line_control.set_lines(self.ref_lines)

    def _sync_ref_lines(self):
        """Push the current reference-line set to both the list view and the plot."""
        self.ref_line_control.set_lines(self.ref_lines)
        self.visualization_widget.set_reference_lines(self.ref_lines)

    def on_view_changed(self):
        """Called when a view-scale toggle (lin/log) changes. Recompute-free redraw."""
        self.logger.info("View scale changed via GUI")
        self._refresh_view()

    def on_plot_refresh_requested(self):
        """Called when manual plot refresh is requested."""
        self.logger.info("Manual plot refresh requested via GUI")
        self._refresh_view()

    def on_metric_compute_started(self, file_path: str, metric_id: str):
        """Called when an off-thread metric compute starts."""
        if file_path not in self._overlay_paths():
            return  # not in the drawn set; status bar shouldn't lie
        metric = METRICS.get(metric_id)
        display = metric.display_name if metric else metric_id
        self.visualization_widget.set_status(f"Computing {display}...")

    def on_metric_ready(self, file_path: str, metric_id: str):
        """Called when metric data is available (cached hit or async finish)."""
        if metric_id != self.plot_control.current_metric_id():
            return  # user already switched to a different metric
        if file_path not in self._overlay_paths():
            return  # no longer part of the overlay set
        self._refresh_view()

    def on_metric_compute_error(self, file_path: str, metric_id: str, error_message: str):
        self.logger.error(f"Metric compute failed ({metric_id} / {os.path.basename(file_path)}): {error_message}")
        if file_path in self._overlay_paths():
            self.visualization_widget.set_status(f"Error computing {metric_id}: {error_message}")

    def _current_file_path(self):
        item = self.file_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _item_for_path(self, file_path):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == file_path:
                return item
        return None

    def _row_index(self, file_path) -> int:
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.UserRole) == file_path:
                return i
        return 0

    def _overlay_paths(self):
        """File paths whose checkbox is ticked — the set drawn on the graph."""
        return [
            self.file_list.item(i).data(Qt.UserRole)
            for i in range(self.file_list.count())
            if self.file_list.item(i).checkState() == Qt.Checked
        ]

    def _refresh_view(self):
        """Redraw the checked overlay set for the current metric and view-state.

        Renders every dataset whose data is cached; for any that isn't, kicks off
        an async compute (or a full load if the file was never analysed) and
        leaves a status note. `on_metric_ready` calls back here when each lands.
        """
        paths = self._overlay_paths()
        metric_id = self.plot_control.current_metric_id()
        view = self.plot_control.current_view_state()
        metric = METRICS.get(metric_id)
        if not paths or metric is None:
            self.visualization_widget.show_specs([])
            return

        specs = []
        pending = 0
        for path in paths:
            data = self.analysis_manager.get_metric_data(path, metric_id)
            if data is None:
                if self.analysis_manager.is_file_analyzed(path):
                    self.analysis_manager.request_metric(path, metric_id)
                else:
                    self.analysis_manager.analyze_file(path, metric_id)
                pending += 1
                continue
            label = self.analysis_manager.display_label(path)
            # Colour is keyed to the file's row, not its position in the overlay
            # subset, so a song keeps its colour as others are ticked/unticked.
            color = dataset_color(self._row_index(path))
            spec = apply_x_mode(metric.build_spec(data, view), view.x_mode)
            specs.append((label, spec, color))

        if specs:
            self.visualization_widget.show_specs(specs, view)
        if pending:
            self.visualization_widget.set_status(
                f"Computing {metric.display_name} for {pending} file(s)..."
            )


def main():
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


if __name__ == '__main__':
    main()