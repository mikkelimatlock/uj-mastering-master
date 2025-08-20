# uj-mastering-master

A custom mastering toolkit that provides metrics to evaluate audio masterings through visual analysis.

## Current Implementation

### Core Features
- **Audio Analysis**: Uses librosa to analyze audio files (MP3/WAV support)
- **Power Visualization**: Generates colorized power magnitude graphs over time
- **Metadata Extraction**: Reads ID3 tags from MP3 files for better file identification
- **GUI Foundation**: Basic PyQt5 drag-and-drop interface (work in progress)

### Technical Stack
- **Audio Processing**: librosa, numpy
- **Visualization**: matplotlib with custom colormaps
- **GUI Framework**: PyQt5 (drag-and-drop functionality)
- **Metadata**: mutagen for MP3 tag reading

### Key Components

#### `master_core.py`
- `AudioFile` class: Main audio processing class
  - Loads audio files and extracts basic metrics (max/avg amplitude, BPM)
  - `get_energy_levels_over_time()`: Calculates RMS power over rolling windows
  - `plot_energy_levels_over_time()`: Creates colorized power graphs with automatic headroom detection
- `analyze_track_librosa()`: Legacy analysis function (dBFS calculations)
- File processing from `files.txt` configuration

#### `main.py`
- PyQt5 drag-and-drop interface
- Currently displays file paths but doesn't integrate with analysis functions
- Placeholder for GUI integration

#### `files.txt`
- Configuration file listing audio files to analyze
- Supports comments (`;` and `#` prefixed lines)
- Currently contains various music file paths

### Current Analysis Features
- **RMS Power Analysis**: 10-second rolling window with 2-second hops
- **Adaptive Color Mapping**: Automatically adjusts scale based on detected headroom
  - High dynamic range: 0-0.6 scale for loud masters
  - Conservative mastering: 0-0.3 scale for quiet masters
- **BPM Detection**: Automatic tempo analysis
- **Metadata Display**: Artist and title from ID3 tags

### Known Issues
- GUI integration incomplete (drag-drop doesn't trigger analysis)
- MP3 tag reading temporarily disabled in some parts
- No interactive features yet implemented

## Future Development Plans

### Short-term Goals
1. **Complete GUI Integration**
   - Connect drag-drop functionality to analysis pipeline
   - Real-time graph display in GUI window
   - File browser for batch processing

2. **Enhanced Metrics**
   - Dynamic range measurement (DR meter)
   - Peak-to-average ratio analysis
   - Frequency spectrum analysis
   - Loudness standards compliance (LUFS)

3. **Interactive Features**
   - Zoom/pan on power graphs
   - Playback controls with visual cursor
   - Export analysis results to CSV/JSON

### Medium-term Goals
1. **Advanced Analysis Tools**
   - Spectral centroid and bandwidth analysis
   - Stereo width measurements
   - Transient detection and analysis
   - Harmonic distortion detection

2. **Comparison Features**
   - Side-by-side track comparison
   - Reference track overlay
   - Mastering version A/B testing

3. **Batch Processing**
   - Folder-based analysis
   - Automated report generation
   - Progress tracking for large collections

### Long-term Vision
1. **VST Plugin Development**
   - Real-time analysis during mixing/mastering
   - Integration with DAWs
   - Live feedback during production

2. **Professional Features**
   - EBU R128 compliance checking
   - Custom target curves
   - Professional reporting formats
   - Multi-format export capabilities

## Development Notes

### Dependencies
- librosa: Audio analysis and feature extraction
- numpy: Numerical computations
- matplotlib: Plotting and visualization
- mutagen: Audio metadata extraction
- PyQt5: GUI framework

### Architecture Considerations
- Current code mixes analysis and visualization - consider separation
- File path handling needs improvement for cross-platform compatibility
- Error handling should be enhanced for production use
- Consider moving from PyQt5 to PyQt6 or PySide for better licensing

### Testing Requirements
- Unit tests for audio analysis functions
- GUI component testing
- File format compatibility testing
- Performance testing with large audio files

## Usage

### Current Usage
1. Add audio file paths to `files.txt`
2. Run `python master_core.py` for batch analysis
3. Run `python main.py` for GUI (incomplete)

### Planned Usage
1. Drag and drop audio files into GUI
2. Real-time analysis with interactive graphs
3. Export reports and comparisons
4. VST plugin for DAW integration