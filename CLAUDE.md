# uj-mastering-master

A custom mastering toolkit that provides metrics to evaluate audio masterings through visual analysis.

## Current implementation

### Core features
- **Audio Analysis**: Uses librosa to analyze audio files (MP3/WAV/FLAC support) at native sample rate (no resampling)
- **Pluggable Metrics**: Switchable visualizations (RMS Power, Waveform, LUFS, Crest Factor, PSR, True Peak, Spectrogram; DR next) via a `Metric` ABC
- **Metadata Extraction**: Reads ID3 tags from MP3 files for better file identification
- **Modular GUI Architecture**: Complete PyQt5 interface with drag-and-drop and file dialog support
- **Font Management**: CJK-capable, fixed UI font (M PLUS 1 Code @ 10pt) with system fallback
- **Threading & Logging**: Robust background processing with detailed logging system

### Technical stack
- **Audio Processing**: librosa, numpy
- **Visualization**: pyqtgraph — persistent, interactive (mouse zoom/pan, lin/log
  toggle, multi-dataset overlay). matplotlib remains only for its colormaps
  (consumed by pyqtgraph) and as a librosa dependency
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
- Persistent pyqtgraph plot — the PlotItem is reused across renders, never torn
  down, so mouse zoom/pan and scale toggles survive every redraw
- `show_specs([(label, PlotSpec), ...], view)` draws one or more datasets onto
  the shared axes, assigning a distinct colour per dataset for overlay/compare
- Spectrogram log-frequency is realised by resampling STFT rows onto a log grid
  (`ImageItem` is affine-only and won't follow a log axis) — see `_render_heatmap`

#### `plotspec.py`
- Backend-agnostic drawing descriptors: `Curve`, `Band`, `HLine`, `Heatmap`,
  `AxisSpec`, `PlotSpec`, plus the `ViewState` (recompute-free lin/log options)
- The seam that decouples metrics from the plotting library: metrics emit
  *intent*, the renderer owns colour/layout/library specifics

#### `font_manager.py`
- Auto-detection of custom fonts from `fonts/` directory; CJK fallbacks
- `apply_fixed_font(family, size)` locks the Qt app font (used at startup to pin
  the UI to **M PLUS 1 Code @ 10pt**, falling back to the system default if the
  family isn't found). There is no runtime font picker — the old
  `font_control_widget.py` was removed as wasted panel space
- pyqtgraph and the Qt widgets both read the app font, so this covers the plot
  too (M PLUS 1 Code has full Japanese coverage, so titles stay CJK-safe)

#### `plot_control_widget.py`
- Metric selector dropdown driven by the `metrics.METRICS` registry
- Log-frequency toggle and a time-axis mode selector — Absolute (seconds) vs
  Relative (% of each track's own length) — both view-state, recompute-free
- `Refresh Plot` button. Compare/overlay membership is the file-list checkboxes;
  reference lines have their own cluster

#### `ref_line_widget.py`
- `RefLineControlWidget`: side-panel list of custom reference lines with
  Add / Edit… / Remove / Clear; a pure view over the `RefLineProps` list the
  main window owns, emitting intents
- `RefLineDialog`: edits one line's value, colour, line style, and tag
- The plot draws each line with a triangle drag-handle; dragging writes the new
  value back into the shared `RefLineProps` and refreshes the list

#### `metrics.py`
- Pluggable `Metric` ABC: `compute(audio_file) -> data` (heavy, worker thread,
  backend-neutral numpy/scalars) and `build_spec(data, view) -> PlotSpec` (cheap,
  GUI thread, view-aware). Metrics no longer touch the plotting library
- Compute-time vs view-time split: scale (lin/log) is a `ViewState` argument to
  `build_spec`, so toggling it never recomputes
- Current registry:
  - `RMSPowerMetric` — 10 s rolling RMS with adaptive colour scale
  - `WaveformMetric` — min/max envelope, fixed ±1.1 y-range
  - `LUFSMetric` — BS.1770 short-term (3 s) + integrated + LRA, via pyloudnorm
  - `CrestFactorMetric` — 20·log10(peak/RMS) per 1 s window
  - `PSRMetric` — sample-peak minus short-term LUFS (3 s window)
  - `TruePeakMetric` — 4× oversampled dBTP via `scipy.signal.resample_poly`
  - `SpectrogramMetric` — log-frequency STFT heatmap; adaptive hop caps time
    bins at ~4000, `N_FFT=4096`. Log/linear frequency is a view toggle
- Drop in new ones (DR, spectral balance) by appending an instance to `METRICS`;
  return a `PlotSpec` from `build_spec` (curves overlay automatically; heatmaps
  show one dataset at a time)
- Note: the old matplotlib `_show_axis_extents` exact-endpoint tick labelling is
  gone with the matplotlib render path. If wanted back, it belongs in the
  renderer, applied uniformly to every metric — not per-metric

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
- **Compare/overlay**: each analysed file has a checkbox; the ticked set is
  overlaid on one graph for the current metric (curve metrics overlay; the
  spectrogram shows one track at a time). Highlighting a row drives the metadata
  panel, independent of the overlay set
- **Interactive plot**: mouse drag-zoom, scroll-wheel zoom, pan, right-click menu
  (pyqtgraph ViewBox); log/linear frequency toggle. Scroll zooms both axes;
  **Ctrl+scroll** zooms time only, **Shift+scroll** zooms the value axis only
  (`_AxisZoomViewBox`); scrolling over an axis also zooms just that axis
- **Time-axis mode**: a Relative-time toggle — off = seconds, on = 0-100% of each
  track's own length, so tracks of very different durations line up by position
- **Custom reference lines**: side-panel list (Add/Edit/Remove/Clear) of draggable
  horizontal markers with value/colour/style/tag; dragged via a triangle handle.
  Kept **per metric** (so switching metrics doesn't lose them) and expressed in
  the metric's own units — on the spectrogram they read and edit in **Hz** (the
  renderer converts Hz<->row index, since the heatmap y-axis is a row index)
- **Plot control**: Metric selector + log-frequency toggle + relative-time toggle
  + refresh-plot button
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

2. **Interactive plot features** *(zoom/pan, axis-range select, lin/log done via
   pyqtgraph)*
   - GUI-controllable plotting styles (colormap, visualization type)
   - Export analysis results to CSV/JSON

3. **Advanced GUI controls**
   - Plot style customization interface
   - Real-time axis range selection (zooming in/out)
   - Interactive plot manipulation tools

4. **Better looking UI**
   - Graphical loading bar
   - Graphical logging text box

### Mid-to-long-term (very not urgent)
1. **Audio comparison system** *(multi-file overlay done via file-list checkboxes;
   each song has a stable palette colour keyed to its list row)*
   - Per-song colour picker: clickable swatch in the file list (overlay already
     accepts a caller-supplied colour per dataset via `show_specs`, so this is a
     UI + override-map addition, not a render change)
   - Reference vs. comparee designation (vs. flat overlay)
   - Side-by-side track comparison interface (incl. spectrogram, which can't overlay)
   - A/B testing for mastering versions

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
- scipy: Signal processing (true-peak polyphase oversampling, spectrogram
  log-frequency resample)
- pyloudnorm: BS.1770 loudness (LUFS, LRA)
- pyqtgraph: Interactive plotting (zoom/pan, overlay, lin/log)
- matplotlib: Colormaps only (consumed by pyqtgraph) + librosa dependency
- mutagen: Audio metadata extraction
- PyQt5: GUI framework

### Architecture considerations
- Three-stage split: `metrics.compute` (heavy, worker thread, backend-neutral
  data) → `metrics.build_spec` (cheap, GUI thread, view-aware `PlotSpec`) →
  `AudioVisualizationWidget.show_specs` (pyqtgraph rendering, overlay, colours)
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