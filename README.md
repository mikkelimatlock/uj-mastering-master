# uj-mastering-master
Utility providing metrics to evaluate masterings.  
Now boosted by Claude Code.

## dependencies
librosa, numpy, matplotlib, mutagen

## usage

### Command Line Analysis
1. Edit `files.txt` to include paths to your audio files (MP3/WAV supported)
   - Use `;` or `#` to comment out files
   - One file path per line
2. Run: `python master_core.py`
   - Generates colorized power magnitude graphs for each file
   - Displays BPM and song metadata
   - Graphs show RMS power over time with adaptive scaling

### GUI Mode (Experimental)
Run: `python main.py`
- Opens drag-and-drop interface
- Currently displays dropped file paths
- Analysis integration coming soon

### Output
- Interactive matplotlib graphs showing power levels over time
- Color-coded visualization (autumn colormap)
- Automatic headroom detection and scaling
- Console output with BPM and metadata information