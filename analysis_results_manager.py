"""
Analysis Results Manager - Bridge between audio processing and GUI.
Manages analysis queue and coordinates between components.
"""

from PyQt5.QtCore import QObject, pyqtSignal
from dataclasses import dataclass
from typing import Optional
import os

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


class AnalysisResultsManager(QObject):
    """
    Manages audio file analysis and coordinates between processing and GUI.
    Threading-ready architecture for future background processing.
    """
    
    # Signals for GUI communication
    analysisStarted = pyqtSignal(str)  # file_path
    analysisCompleted = pyqtSignal(str, object)  # file_path, AnalysisResult
    analysisError = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self):
        super().__init__()
        self.results_cache = {}  # Store analysis results
        self.plotting_engine = PlottingEngine()
    
    def analyze_file(self, file_path: str, window: int = 10, hop: int = 2):
        """
        Analyze an audio file and emit results.
        Currently synchronous - ready for threading later.
        
        Args:
            file_path: Path to audio file
            window: RMS analysis window size in seconds
            hop: Analysis hop size in seconds
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.analysisError.emit(file_path, error_msg)
            return
            
        # Emit analysis started signal
        self.analysisStarted.emit(file_path)
        
        try:
            # Create AudioFile and perform analysis
            audio_file = AudioFile(file_path)
            
            # Get RMS analysis data
            audio_file.get_energy_levels_over_time(window=window, hop=hop)
            
            # Extract analysis results
            result = AnalysisResult(
                file_path=file_path,
                song_name=audio_file.song_name,
                bpm=audio_file.get_bpm(),
                max_amplitude=audio_file.max_amplitude,
                avg_amplitude=audio_file.avg_amplitude,
                times=audio_file._get_times(),  # We'll need to add this method
                rms_array=audio_file.rms_array,
                analysis_successful=True
            )
            
            # Cache the result
            self.results_cache[file_path] = result
            
            # Emit completion signal
            self.analysisCompleted.emit(file_path, result)
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            self.analysisError.emit(file_path, error_msg)
    
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