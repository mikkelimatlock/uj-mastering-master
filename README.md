# uj-mastering-master

Custom mastering toolkit providing visual metrics for evaluating audio masterings.
Developed with Claude Code assistance.

## Features

### Current
- **PyQt5 GUI**: drag-and-drop or file-dialog ingest of `.mp3`, `.wav`, `.flac`
- **Switchable metrics** via a dropdown, all sharing one analysis cache:
  - **RMS Power** — 10 s rolling window with adaptive colour scale
  - **Waveform** — min/max envelope, fixed ±1.1 scale
  - **LUFS** — BS.1770 short-term (3 s) + integrated + loudness range (LRA)
  - **Crest Factor** — peak-to-RMS spread over time
  - **PSR** — peak-to-short-term-loudness ratio ("is it still breathing?")
  - **True Peak** — 4× oversampled dBTP, catches inter-sample peaks
  - **Spectrogram** — log-frequency STFT power heatmap over time
- **Always-labelled axis extremes**: every plot forces its exact min/max onto
  the ticks, so you can read the true range even on a log axis (e.g. the
  spectrogram's 22 kHz top, which otherwise falls between decade ticks)
- **Native sample rate**: audio is loaded without resampling, so the full band
  (up to the file's own nyquist, e.g. ~22 kHz for 44.1 kHz files) is analysed
- **BPM detection** via librosa
- **CJK-safe font system** with custom fonts loaded from `fonts/` (gitignored), system fallbacks, and a live font selector
- **Background analysis thread** so the UI stays responsive; metric switches
  compute off the GUI thread and cache, so re-selecting a metric is instant
- **Embedded matplotlib canvas** with auto-regenerated plots on font change

### Roadmap
See [CLAUDE.md](CLAUDE.md) for the full development roadmap. Near-term:
dynamic range (DR meter), plot-style controls, interactive axis controls.

## Quick start

This project uses [uv](https://docs.astral.sh/uv/). With uv installed:

```bash
uv sync
uv run ujm
```

`uv run ujm` is the only supported entry point — it boots the GUI.

### Logging flags
```bash
uv run ujm --log-level DEBUG       # ERROR | WARN | INFO | DEBUG | TRACE
uv run ujm --log-file               # also write audio_analysis.log
```

### Fonts
Drop `.ttf` / `.otf` / `.ttc` files into `fonts/` to get them in the font
selector. The directory is gitignored to avoid bundling licensed font data.
See [CJK_FONTS.md](CJK_FONTS.md) for details.

## Dependencies
`librosa`, `numpy`, `matplotlib`, `mutagen`, `pyloudnorm`, `PyQt5` — all pinned
through `uv.lock`. Python 3.10+.

## Architecture

| Module | Responsibility |
| --- | --- |
| `main.py` | `MainWindow` + the `ujm` entry point |
| `analysis_results_manager.py` | Background `QThread` worker, result + metric-data cache |
| `master_core.py` | `AudioFile`: native-rate librosa loading, RMS rolling window, BPM |
| `metrics.py` | Pluggable `Metric` ABC + registry (RMS, Waveform, LUFS, Crest, PSR, True Peak, Spectrogram) |
| `audio_visualization_widget.py` | Embedded `FigureCanvasQTAgg` host |
| `font_manager.py` | Custom + system CJK font discovery, matplotlib/Qt config |
| `font_control_widget.py` | Font picker + size slider |
| `plot_control_widget.py` | Metric selector + refresh-plot button |
| `logger_setup.py` | CLI log-level parsing + custom TRACE level |
| `setup_fonts.py` | Diagnostic utility (run standalone) |

### Adding a metric

Subclass `Metric` in `metrics.py`, implement `compute(audio_file) -> data` (the
heavy part, runs on the worker thread) and `render(data, file_path) -> Figure`
(cheap, runs on the GUI thread). Register the instance in the `METRICS` dict at
the bottom of the file — it shows up in the dropdown automatically.
