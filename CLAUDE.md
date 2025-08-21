# uj-mastering-master

A custom mastering toolkit that provides metrics to evaluate audio masterings through visual analysis.

## Current Implementation

### Core Features
- **Audio Analysis**: Uses librosa to analyze audio files (MP3/WAV/FLAC support)
- **Power Visualization**: Generates colorized power magnitude graphs over time
- **Metadata Extraction**: Reads ID3 tags from MP3 files for better file identification
- **Modular GUI Architecture**: Complete PyQt5 interface with drag-and-drop and file dialog support
- **Font Management**: Comprehensive CJK-compatible font system with user-provided font support
- **Threading & Logging**: Robust background processing with detailed logging system

### Technical Stack
- **Audio Processing**: librosa, numpy
- **Visualization**: matplotlib with custom colormaps and embedded Qt widgets
- **GUI Framework**: PyQt5 with modular widget architecture
- **Metadata**: mutagen for audio tag reading
- **Font Support**: Custom font loading system with CJK fallback

### Key Components

#### `main.py`
- Complete GUI application with modular architecture
- Drag-and-drop and file dialog support for audio files
- Integrated font control system
- Real-time analysis display and file management

#### `analysis_results_manager.py`
- Background threading for audio analysis
- Results caching and management
- Progress tracking and error handling

#### `audio_visualization_widget.py`
- Embedded matplotlib visualization with Qt integration
- Real-time plot updates and status display

#### `font_control_widget.py` & `font_manager.py`
- Unified font control system with clustered interface
- Auto-detection of custom fonts from `fonts/` directory
- System font discovery and CJK compatibility
- Auto-regeneration of plots when fonts change

#### `master_core.py`
- Core audio analysis functionality
- `AudioFile` class with comprehensive metrics extraction
- RMS power analysis and BPM detection

### Current Analysis Features
- **RMS Power Analysis**: 10-second rolling window with 2-second hops
- **Adaptive Color Mapping**: Automatically adjusts scale based on detected headroom
  - High dynamic range: 0-0.6 scale for loud masters  
  - Conservative mastering: 0-0.3 scale for quiet masters
- **BPM Detection**: Automatic tempo analysis
- **Metadata Display**: Artist and title from audio tags
- **Real-time Visualization**: Embedded matplotlib plots with font-aware rendering

### GUI Features
- **File Management**: Drag-and-drop and file dialog for audio selection
- **Font Control**: Unified font selector with size control and plot regeneration
- **Analysis Display**: Real-time visualization with metadata panels
- **Modular Architecture**: Self-contained widgets for easy layout management

## Future Development Plans

### Short-term (Urgent)
1. **Plot Control Widget Cluster**
   - Move 'Refresh Plot' into dedicated plot/graph widget cluster
   - Add metric selection widget (choose which analysis to display)
   - Implement plot style controller (colormap, line vs bar, etc.)
   - Prepare foundation for mastering comparison features

### Short-term (Not Urgent)
1. **Enhanced Metrics**
   - LUFS loudness measurement implementation
   - Dynamic range measurement (DR meter)
   - Peak-to-average ratio analysis
   - Frequency spectrum analysis

2. **Interactive Plot Features**
   - GUI-controllable plotting styles (colormap, visualization type)
   - Select axis ranges on the fly with automatic graph updates
   - Zoom/pan controls for detailed analysis
   - Export analysis results to CSV/JSON

3. **Advanced GUI Controls**
   - Plot style customization interface
   - Real-time axis range selection
   - Interactive plot manipulation tools

### Mid-Long term (Not Urgent)
1. **Audio Comparison System**
   - Reference vs. comparee audio file analysis
   - Side-by-side track comparison interface
   - A/B testing for mastering versions
   - Overlay visualization for comparative analysis

2. **Distribution & Deployment**
   - Self-contained executable releases
   - Cross-platform packaging
   - Installer creation and distribution

### Future Vision
1. **Advanced Analysis Tools**
   - Spectral centroid and bandwidth analysis
   - Stereo width measurements
   - Transient detection and analysis
   - Harmonic distortion detection

2. **Professional Features**
   - EBU R128 compliance checking
   - Custom target curves
   - Professional reporting formats
   - Multi-format export capabilities

3. **VST Plugin Development**
   - Real-time analysis during mixing/mastering
   - Integration with DAWs
   - Live feedback during production

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
1. Run `python main.py` to launch the GUI application
2. Use "Open Audio File..." button or drag-and-drop audio files for analysis
3. Adjust font settings using the Font Settings panel
4. View real-time analysis results with embedded matplotlib plots
5. Select different analyzed files from the file list to compare results

### Legacy Usage (Batch Mode)
1. Add audio file paths to `files.txt`
2. Run `python master_core.py` for batch analysis

### Planned Usage Enhancements
1. Interactive plot manipulation and style customization
2. LUFS and advanced metric analysis
3. Audio file comparison features
4. Self-contained executable releases