# uj-mastering-master
Custom mastering toolkit providing comprehensive metrics to evaluate audio masterings through visual analysis.  
Developed with Claude Code assistance.

## Features

### ✅ Current Implementation
- **Complete GUI Application**: Modular PyQt5 interface with drag-and-drop and file dialog support
- **Real-time Analysis**: Background threading with embedded matplotlib visualization
- **Font Management**: CJK-compatible font system with custom font support from `fonts/` directory
- **Audio Support**: MP3, WAV, and FLAC file analysis
- **RMS Power Analysis**: Rolling window analysis with adaptive color mapping
- **Metadata Display**: Automatic extraction and display of audio tags and BPM

### 🚧 In Development
- **Plot Control Widgets**: Dedicated cluster for plot manipulation and style controls
- **LUFS Metrics**: Professional loudness measurement implementation
- **Interactive Plotting**: Real-time axis control and style customization

### 🔮 Planned Features
- **Audio Comparison**: Reference vs. comparee analysis for mastering evaluation
- **Advanced Metrics**: Dynamic range, spectral analysis, and professional standards compliance
- **Standalone Releases**: Self-contained executable distribution

## Dependencies
- **Core**: `librosa`, `numpy`, `matplotlib`, `mutagen`
- **GUI**: `PyQt5`
- **Audio Processing**: Advanced librosa-based analysis pipeline

## Usage

### GUI Application (Recommended)
```bash
python main.py
```
- **Load Files**: Use "Open Audio File..." button or drag-and-drop
- **Font Control**: Adjust interface fonts and regenerate plots automatically  
- **Analysis Display**: View real-time RMS power analysis with metadata
- **File Management**: Switch between analyzed files using the file list

### Command Line Analysis (Legacy)
```bash
# 1. Edit files.txt with your audio file paths
# 2. Run batch analysis
python master_core.py
```

## Architecture

### Modular Design
- **Self-contained Widgets**: Easy layout management and customization
- **Background Processing**: Non-blocking analysis with progress feedback
- **Signal-based Communication**: Clean separation between GUI and analysis logic

### Key Components
- `main.py`: Complete GUI application with modular architecture
- `font_control_widget.py`: Unified font management with plot regeneration
- `analysis_results_manager.py`: Threaded analysis with caching
- `audio_visualization_widget.py`: Embedded matplotlib with Qt integration

## Development Roadmap

### 🎯 Next Priority: Plot Control System
Moving from font-focused interface to comprehensive plot manipulation:
- Cluster plot controls (refresh, style, metric selection)
- Interactive axis range selection
- Real-time plot style customization
- Foundation for comparison features

### 🎵 Short-term Goals
- **LUFS Implementation**: Professional loudness standards
- **Plot Interactivity**: GUI-controlled visualization styles
- **Metric Selection**: Choose which analysis to display

### 🎼 Long-term Vision
- **Mastering Comparison**: Side-by-side analysis tools
- **Professional Standards**: EBU R128 compliance checking
- **Standalone Distribution**: Self-contained executable releases