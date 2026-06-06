# uj-mastering-master

A custom mastering toolkit that provides metrics to evaluate audio masterings through visual analysis.

## Current implementation

### Core features
- **Audio Analysis**: Uses librosa to analyze audio files (MP3/WAV/FLAC support) at native sample rate (no resampling)
- **Pluggable Metrics**: Switchable visualizations (RMS Power, Waveform, LUFS, Crest Factor, PSR, True Peak, Spectrogram; DR next) via a `Metric` ABC
- **Metadata Extraction**: Reads ID3 tags from MP3 files for better file identification
- **Modular GUI Architecture**: Complete PyQt5 interface with drag-and-drop and file dialog support
- **Font Management**: Comprehensive CJK-compatible font system with user-provided font support
- **Threading & Logging**: Robust background processing with detailed logging system

### Technical stack
- **Audio Processing**: librosa, numpy
- **Visualization**: matplotlib with custom colormaps and embedded Qt widgets
- **GUI Framework**: PyQt5 with modular widget architecture
- **Metadata**: mutagen for audio tag reading
- **Font Support**: Custom font loading system with CJK fallback

### Key components

#### `main.py`
- Complete GUI application with modular architecture
- Drag-and-drop and file dialog support for audio files
- Integrated font control system
- Real-time analysis display and file management

#### `analysis_results_manager.py`
- Background threading for audio analysis
- Caches both the loaded `AudioFile` and per-metric `compute()` output, so
  metric/font switches re-render from cache without reloading librosa
- Progress tracking and error handling

#### `audio_visualization_widget.py`
- Embedded matplotlib visualization with Qt integration
- Real-time plot updates and status display

#### `font_control_widget.py` & `font_manager.py`
- Unified font control system with clustered interface
- Auto-detection of custom fonts from `fonts/` directory
- System font discovery and CJK compatibility
- Font changes trigger a cheap re-render of the cached metric data

#### `plot_control_widget.py`
- Metric selector dropdown driven by the `metrics.METRICS` registry
- Houses the `Refresh Plot` button (foundation for upcoming style controls)

#### `metrics.py`
- Pluggable `Metric` ABC: `compute(audio_file) -> data` (heavy, worker thread)
  and `render(data, file_path) -> Figure` (cheap, GUI thread)
- Current registry:
  - `RMSPowerMetric` — 10 s rolling RMS with adaptive colour scale
  - `WaveformMetric` — min/max envelope, fixed ±1.1 y-range
  - `LUFSMetric` — BS.1770 short-term (3 s) + integrated + LRA, via pyloudnorm
  - `CrestFactorMetric` — 20·log10(peak/RMS) per 1 s window
  - `PSRMetric` — sample-peak minus short-term LUFS (3 s window)
  - `TruePeakMetric` — 4× oversampled dBTP via `scipy.signal.resample_poly`
  - `SpectrogramMetric` — log-frequency STFT heatmap; adaptive hop caps time
    bins at ~4000, `N_FFT=4096`
- Shared render helpers: `_show_axis_extents(ax)` forces each axis's exact
  min/max onto the ticks (so log-axis extremes like 22 kHz are always
  labelled); `_fmt_tick` keeps those labels compact
- Drop in new ones (DR, spectral balance) by appending an instance to `METRICS`

#### `master_core.py`
- Defines the `AudioFile` class: librosa loading, rolling RMS power, BPM detection
- Loads at **native sample rate** (`librosa.load(..., sr=None)`) so the full
  band is preserved — analysis runs ~2× heavier on 44.1/48 kHz files than the
  old 22050 Hz default, by design
- No batch / CLI mode — all analysis is driven from `main.py` via `AnalysisResultsManager`

### Current analysis features
- **Native-rate loading**: full-band analysis up to the file's own nyquist
- **RMS power analysis**: 10-second rolling window with 2-second hops
- **Adaptive colour mapping**: Automatically adjusts scale based on detected headroom
  - High dynamic range: 0-0.6 scale for loud masters  
  - Conservative mastering: 0-0.3 scale for quiet masters
- **Loudness metrics**: LUFS (short-term + integrated + LRA), PSR, Crest Factor
- **Peak analysis**: True Peak (4× oversampled dBTP)
- **Spectral view**: log-frequency spectrogram heatmap over time
- **Readable axes**: exact min/max of every axis is always labelled, even on log scale
- **BPM detection**: Automatic tempo analysis
- **Metadata display**: Artist and title from audio tags
- **Real-time visualization**: Embedded matplotlib plots with font-aware rendering

### GUI features
- **File management**: Drag-and-drop and file dialog for audio selection
- **Font control**: Unified font selector with size control
- **Plot control**: Metric selector + refresh-plot button
- **Analysis display**: Real-time visualization with metadata panels
- **Modular architecture**: Self-contained widgets for easy layout management

## Future development plans

### Short-term (urgent)
1. **Plot control widget cluster** *(metric selector + Refresh Plot done; still TODO)*
   - Plot style controller (colormap, line vs bar, etc.)
   - Foundation for mastering comparison features

### Short-term (not urgent)
1. **Enhanced metrics** *(plug new ones into `metrics.METRICS`)*
   - Dynamic range measurement (DR meter)
   - Long-term average spectrum (LTAS) / tonal-balance curve
   - Stereo metrics (correlation, mid/side) — needs `AudioFile` to retain stereo

2. **Interactive plot features**
   - GUI-controllable plotting styles (colormap, visualization type)
   - Select axis ranges on the fly with automatic graph updates
   - Zoom/pan controls for detailed analysis
   - Export analysis results to CSV/JSON

3. **Advanced GUI controls**
   - Plot style customization interface
   - Real-time axis range selection (zooming in/out)
   - Interactive plot manipulation tools

4. **Better looking UI**
   - Graphical loading bar
   - Graphical logging text box

### Mid-to-long-term (very not urgent)
1. **Audio comparison system**
   - Reference vs. comparee audio file analysis
   - Side-by-side track comparison interface
   - A/B testing for mastering versions
   - Overlay visualization for comparative analysis

2. **Distribution & deployment**
   - Self-contained executable releases
   - Cross-platform packaging
   - Installer creation and distribution

### Future vision
1. **Advanced analysis tools**
   - Spectral centroid and bandwidth analysis
   - Stereo width measurements
   - Transient detection and analysis
   - Harmonic distortion detection

2. **Professional features**
   - EBU R128 compliance checking
   - Custom target curves
   - Professional reporting formats
   - Multi-format export capabilities

3. **VST plugin development**
   - Real-time analysis during mixing/mastering
   - Integration with DAWs
   - Live feedback during production

## Development notes

### Dependencies
- librosa: Audio analysis and feature extraction
- numpy: Numerical computations
- scipy: Signal processing (true-peak polyphase oversampling)
- pyloudnorm: BS.1770 loudness (LUFS, LRA)
- matplotlib: Plotting and visualization
- mutagen: Audio metadata extraction
- PyQt5: GUI framework

### Architecture considerations
- Analysis (`metrics.compute`) and visualization (`metrics.render`) are split
  across the `Metric` ABC; compute runs on a worker thread, render on the GUI
- File path handling needs improvement for cross-platform compatibility
- Error handling should be enhanced for production use
- Consider moving from PyQt5 to PyQt6 or PySide for better licensing

### Testing requirements
- Unit tests for audio analysis functions
- GUI component testing
- File format compatibility testing
- Performance testing with large audio files

## Usage

### Running the app
```bash
uv sync          # one-time, after cloning
uv run ujm       # launch the GUI
```

Optional flags (handled by `logger_setup.parse_log_args`):
```bash
uv run ujm --log-level DEBUG    # ERROR | WARN | INFO | DEBUG | TRACE
uv run ujm --log-file            # also write audio_analysis.log
```

The only entry point is `ujm` (defined in `pyproject.toml` as
`ujm = "main:main"`). The previous `files.txt` batch mode and the
`python master_core.py` workflow have been removed.

### Planned usage enhancements
1. Interactive plot manipulation and style customization
2. Audio file comparison features (reference vs. comparee)
3. Self-contained executable releases