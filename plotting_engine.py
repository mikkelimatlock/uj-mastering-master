"""
Audio visualization plotting engine.
Separates plotting logic from audio processing for clean GUI integration.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.figure import Figure
import os


class PlottingEngine:
    """Handles all matplotlib visualization logic for audio analysis."""
    
    @staticmethod
    def create_power_analysis_figure(times, rms_array, file_path, figsize=(10, 4)):
        """
        Creates a matplotlib Figure for power analysis visualization.
        
        Args:
            times: Array of time points
            rms_array: RMS power values over time
            file_path: Path to the audio file for title
            figsize: Figure size tuple
            
        Returns:
            matplotlib.figure.Figure: Ready-to-embed figure
        """
        # Determine color scale based on headroom detection
        local_max_power = np.max(rms_array)
        if local_max_power > 0.3:
            norm = mcolors.Normalize(vmin=0, vmax=0.6)
            maxpower = 0.6
        else:
            norm = mcolors.Normalize(vmin=0, vmax=0.3)
            maxpower = 0.3
        
        # Create figure and axis
        fig = Figure(figsize=figsize, facecolor='white')
        ax = fig.add_subplot(111)
        
        # Color map
        cmap = cm.autumn
        
        # Plot power levels as colored bars
        ax.set_ylim(0., maxpower)
        for i in range(len(times)-1):
            ax.fill_between(times[i:i+2], 0, rms_array[0][i], 
                          color=cmap(norm(rms_array[0][i])), edgecolor='none')
        
        # Add colorbar
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, label='RMS Power')
        
        # Labels and title
        ax.set_ylabel('Power')
        ax.set_xlabel('Time (seconds)')
        ax.set_title(f'{os.path.basename(file_path)}')
        
        # Tight layout for better appearance in GUI
        fig.tight_layout()
        
        return fig
    
    @staticmethod
    def create_metadata_display_text(song_name, bpm, max_amplitude, avg_amplitude):
        """
        Creates formatted text for metadata display.
        
        Returns:
            str: Formatted metadata text
        """
        return f"""Track: {song_name}
BPM: {bpm:.1f}
Max Amplitude: {max_amplitude:.3f}
Avg Amplitude: {avg_amplitude:.3f}"""