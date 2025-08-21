"""
Analysis Results Manager - Bridge between audio processing and GUI.
Manages analysis queue and coordinates between components.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread
from dataclasses import dataclass
from typing import Optional
import os
import logging

from master_core import AudioFile
from plotting_engine import PlottingEngine


@dataclass
class AnalysisResult:
    """Container for audio analysis results."""
    file_path: str
    song_name: str
    bpm: float
    max_amplitude: float
    avg_amplitude: float
    times: list
    rms_array: list
    analysis_successful: bool = True
    error_message: str = ""


class AudioAnalysisWorker(QThread):
    """
    Worker thread for audio analysis to prevent GUI freezing.
    Performs heavy librosa operations in background.
    """
    
    # Signals for communicating with main thread
    progressUpdate = pyqtSignal(str, int)  # message, percentage
    analysisCompleted = pyqtSignal(str, object)  # file_path, AnalysisResult
    analysisError = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self, file_path: str, window: int = 10, hop: int = 2):
        super().__init__()
        self.file_path = file_path
        self.window = window
        self.hop = hop
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Main thread execution - performs audio analysis."""
        try:
            self.logger.info(f"Starting analysis of: {os.path.basename(self.file_path)}")
            self.progressUpdate.emit("Loading audio file...", 10)
            
            # Create AudioFile and load audio data
            audio_file = AudioFile(self.file_path)
            self.progressUpdate.emit("Audio loaded, detecting tempo...", 30)
            
            # BPM is already calculated in __init__, now do RMS analysis
            self.progressUpdate.emit("Computing RMS power levels...", 60)
            audio_file.get_energy_levels_over_time(window=self.window, hop=self.hop)
            
            self.progressUpdate.emit("Finalizing analysis...", 90)
            
            # Extract analysis results
            result = AnalysisResult(
                file_path=self.file_path,
                song_name=audio_file.song_name,
                bpm=audio_file.get_bpm(),
                max_amplitude=audio_file.max_amplitude,
                avg_amplitude=audio_file.avg_amplitude,
                times=audio_file._get_times(),
                rms_array=audio_file.rms_array,
                analysis_successful=True
            )
            
            self.progressUpdate.emit("Analysis complete!", 100)
            self.logger.info(f"Analysis completed: {os.path.basename(self.file_path)} (BPM: {result.bpm:.1f})")
            
            # Emit success signal
            self.analysisCompleted.emit(self.file_path, result)
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            self.logger.error(f"Analysis error for {self.file_path}: {error_msg}")
            self.analysisError.emit(self.file_path, error_msg)


class AnalysisResultsManager(QObject):
    """
    Manages audio file analysis and coordinates between processing and GUI.
    Now uses background threads to prevent GUI freezing.
    """
    
    # Signals for GUI communication
    analysisStarted = pyqtSignal(str)  # file_path
    analysisCompleted = pyqtSignal(str, object)  # file_path, AnalysisResult
    analysisError = pyqtSignal(str, str)  # file_path, error_message
    progressUpdate = pyqtSignal(str, int)  # message, percentage
    
    def __init__(self):
        super().__init__()
        self.results_cache = {}  # Store analysis results
        self.plotting_engine = PlottingEngine()
        self.current_worker = None  # Track active worker thread
        self.logger = logging.getLogger(__name__)
    
    def analyze_file(self, file_path: str, window: int = 10, hop: int = 2):
        """
        Analyze an audio file using background thread to prevent GUI freezing.
        
        Args:
            file_path: Path to audio file
            window: RMS analysis window size in seconds
            hop: Analysis hop size in seconds
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            self.analysisError.emit(file_path, error_msg)
            return
        
        # Stop any existing worker
        if self.current_worker and self.current_worker.isRunning():
            self.logger.info("Stopping previous analysis to start new one")
            self.current_worker.quit()
            self.current_worker.wait()
            
        # Emit analysis started signal
        self.analysisStarted.emit(file_path)
        self.logger.info(f"Queuing analysis: {os.path.basename(file_path)}")
        
        # Create and start worker thread
        self.current_worker = AudioAnalysisWorker(file_path, window, hop)
        
        # Connect worker signals
        self.current_worker.progressUpdate.connect(self.progressUpdate.emit)
        self.current_worker.analysisCompleted.connect(self._on_worker_completed)
        self.current_worker.analysisError.connect(self.analysisError.emit)
        
        # Start the background analysis
        self.current_worker.start()
    
    def _on_worker_completed(self, file_path: str, result: AnalysisResult):
        """Handle completion of worker thread analysis."""
        # Cache the result
        self.results_cache[file_path] = result
        
        # Forward the signal to GUI
        self.analysisCompleted.emit(file_path, result)
    
    def get_analysis_figure(self, file_path: str):
        """
        Get matplotlib figure for a previously analyzed file.
        
        Returns:
            matplotlib.figure.Figure or None
        """
        if file_path not in self.results_cache:
            return None
            
        result = self.results_cache[file_path]
        return self.plotting_engine.create_power_analysis_figure(
            result.times, result.rms_array, result.file_path
        )
    
    def get_metadata_text(self, file_path: str) -> str:
        """Get formatted metadata text for a file."""
        if file_path not in self.results_cache:
            return "No analysis data available"
            
        result = self.results_cache[file_path]
        return self.plotting_engine.create_metadata_display_text(
            result.song_name, result.bpm, 
            result.max_amplitude, result.avg_amplitude
        )
    
    def clear_cache(self):
        """Clear all cached analysis results."""
        self.results_cache.clear()
    
    def is_file_analyzed(self, file_path: str) -> bool:
        """Check if a file has been analyzed."""
        return file_path in self.results_cache