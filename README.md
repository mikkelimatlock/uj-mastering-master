# uj-mastering-master

Custom mastering toolkit providing visual metrics for evaluating audio masterings.
Developed with Claude Code assistance.

## Features

### Current
- **PyQt5 GUI**: drag-and-drop or file-dialog ingest of `.mp3`, `.wav`, `.flac`
- **RMS power analysis** on a 10 s rolling window with adaptive colour scale
- **BPM detection** via librosa
- **CJK-safe font system** with custom fonts loaded from `fonts/` (gitignored), system fallbacks, and a live font selector
- **Background analysis thread** so the UI stays responsive
- **Embedded matplotlib canvas** with auto-regenerated plots on font change

### Roadmap
See [CLAUDE.md](CLAUDE.md) for the full development roadmap. Near-term:
plot-control widget cluster, LUFS, dynamic range, interactive axis controls.

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
`librosa`, `numpy`, `matplotlib`, `mutagen`, `PyQt5` — all pinned through
`uv.lock`. Python 3.10+.

## Architecture

| Module | Responsibility |
| --- | --- |
| `main.py` | `MainWindow` + the `ujm` entry point |
| `analysis_results_manager.py` | Background `QThread` worker, result cache |
| `master_core.py` | `AudioFile`: librosa loading, RMS rolling window, BPM |
| `plotting_engine.py` | Matplotlib `Figure` builder for the power graph |
| `audio_visualization_widget.py` | Embedded `FigureCanvasQTAgg` host |
| `font_manager.py` | Custom + system CJK font discovery, matplotlib/Qt config |
| `font_control_widget.py` | Font picker, size slider, refresh-plot button |
| `logger_setup.py` | CLI log-level parsing + custom TRACE level |
| `setup_fonts.py` | Diagnostic utility (run standalone) |
