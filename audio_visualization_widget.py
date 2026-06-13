"""
Interactive visualization widget built on pyqtgraph.

One persistent PlotItem that is *reused* across renders — never torn down — so
mouse zoom/pan, the view box, and scale toggles all survive redraws. Consumes a
list of `(label, PlotSpec)` pairs and draws them onto the same axes, using a
caller-supplied colour per dataset so a song keeps its colour regardless of which
others are overlaid.

Interaction notes:
- Plain scroll zooms both axes; Ctrl+scroll zooms time only; Shift+scroll zooms
  the value axis only (see `_AxisZoomViewBox`). Scrolling directly over an axis
  also zooms just that axis (pyqtgraph default).
- User reference lines (`add_user_line`) are draggable, survive redraws within a
  metric, and are cleared by the GUI when the metric changes (units change).

Why the spectrogram is special: pyqtgraph's ImageItem is affine-only, so it does
not follow a log-scaled axis. Log frequency is therefore realised by resampling
the STFT rows onto a log-spaced grid and labelling the axis by row index — see
`_render_heatmap`.
"""

import numpy as np
import pyqtgraph as pg
from scipy.interpolate import interp1d
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from plotspec import PlotSpec, ViewState, DEFAULT_VIEW

# White canvas / black ink to match the previous matplotlib aesthetic.
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)

# Dataset colour cycle for overlay. First colour is the single-dataset default.
_PALETTE = [
  "#3a7ad6", "#e76f51", "#2a9d8f", "#e09f3e",
  "#7251b5", "#c1121f", "#588157", "#9d4edd",
]

# Pen styles for reference lines.
_PEN_STYLE = {"solid": Qt.SolidLine, "dash": Qt.DashLine, "dot": Qt.DotLine}

# "Nice" frequencies to label on a log frequency axis, in Hz.
_LOG_FREQ_TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]

# Colour for user-added reference lines (neutral so it reads on any metric).
_USER_LINE_COLOR = "#444444"


def dataset_color(index: int) -> str:
  """Stable dataset colour for a given index (e.g. a file's row in the list)."""
  return _PALETTE[index % len(_PALETTE)]


def _colormap(name: str):
  """Fetch a colormap, preferring matplotlib's so 'magma' etc. resolve."""
  try:
    return pg.colormap.getFromMatplotlib(name)
  except Exception:
    return pg.colormap.get(name)


def _fmt_hz(hz: float) -> str:
  return f"{hz / 1000:.0f}k" if hz >= 1000 else f"{hz:.0f}"


class _AxisZoomViewBox(pg.ViewBox):
  """ViewBox whose wheel zoom can be constrained to one axis via a modifier.

  Plain scroll keeps pyqtgraph's both-axes zoom; Ctrl constrains to x (time),
  Shift constrains to y (the metric's value axis). This answers the "scroll
  zooms both axes, I want one" problem without taking away the default.
  """

  def wheelEvent(self, ev, axis=None):
    mods = ev.modifiers()
    if mods & Qt.ControlModifier:
      axis = 0  # x only
    elif mods & Qt.ShiftModifier:
      axis = 1  # y only
    super().wheelEvent(ev, axis=axis)


class AudioVisualizationWidget(QWidget):
  """Persistent interactive plot. Call `show_specs` to (re)draw."""

  def __init__(self, parent=None):
    super().__init__(parent)
    layout = QVBoxLayout(self)

    self.glw = pg.GraphicsLayoutWidget()
    self.plot = self.glw.addPlot(row=0, col=0, viewBox=_AxisZoomViewBox())
    self.plot.showGrid(x=True, y=True, alpha=0.3)
    self.plot.setMenuEnabled(True)
    self.legend = self.plot.addLegend(offset=(-10, 10))
    layout.addWidget(self.glw)

    self.status_label = QLabel("Ready for audio analysis...")
    layout.addWidget(self.status_label)

    self._colorbar = None
    # User reference lines persist by value across redraws; the items are rebuilt
    # each render. Cleared by the GUI on metric change (units change).
    self._user_line_values: list[float] = []
    self._user_lines: list[pg.InfiniteLine] = []
    self._show_empty()

  # ---- public API ---------------------------------------------------------

  def show_specs(self, specs, view: ViewState = DEFAULT_VIEW):
    """Render datasets onto the shared axes.

    `specs` is a list of `(label, PlotSpec)` or `(label, PlotSpec, color)`. When
    no colour is given, the dataset's palette colour by position is used. All
    specs are assumed to be the same metric (compare overlays one metric across
    files), so axis labels/ranges come from the first spec.
    """
    self._reset_plot()
    if not specs:
      self._show_empty()
      return

    specs = [self._normalise(s, i) for i, s in enumerate(specs)]
    base_axes = specs[0][1].axes

    # Heatmaps do not overlay: render only the first dataset's heatmap.
    if specs[0][1].is_heatmap:
      label, spec, _ = specs[0]
      self._render_heatmap(spec, view)
      if len(specs) > 1:
        self.set_status(f"{spec.title or label}: spectrogram shows one track at a time")
      self._apply_axes(base_axes, log_y_image_handled=True)
      self._draw_user_lines()
      return

    single = len(specs) == 1
    for label, spec, color in specs:
      prefix = "" if single else f"{label}: "
      self._render_curves_and_bands(spec, color, prefix, single=single)

    # Reference lines from the first spec only (identical across same-metric specs).
    for hl in specs[0][1].hlines:
      self._render_hline(hl)

    # Scalar readouts → legend-only proxy entries.
    for label, spec, _ in specs:
      prefix = "" if single else f"{label}: "
      for note in spec.annotations:
        self._legend_note(prefix + note)

    self._apply_axes(base_axes)
    self._draw_user_lines()

  def add_user_line(self, value: float | None = None):
    """Add a draggable horizontal reference line at `value` (default: view centre)."""
    if value is None:
      (_, _), (y0, y1) = self.plot.viewRange()
      value = (y0 + y1) / 2.0
    self._user_line_values.append(float(value))
    self._draw_user_lines()

  def clear_user_lines(self):
    """Remove all user reference lines (called when the metric changes)."""
    self._user_line_values.clear()
    self._remove_user_line_items()

  def set_status(self, message: str):
    self.status_label.setText(message)

  # ---- rendering helpers --------------------------------------------------

  def _normalise(self, spec_tuple, index: int):
    """Coerce a spec tuple to (label, PlotSpec, color), filling colour by index."""
    if len(spec_tuple) == 3:
      return spec_tuple
    label, spec = spec_tuple
    return label, spec, dataset_color(index)

  def _render_curves_and_bands(self, spec: PlotSpec, color: str, prefix: str, single: bool):
    for band in spec.bands:
      lo = np.ascontiguousarray(np.broadcast_to(band.lo, band.x.shape), dtype=float)
      hi = np.ascontiguousarray(np.broadcast_to(band.hi, band.x.shape), dtype=float)
      # FillBetweenItem fills nothing if its child curves have no pen — give them
      # a thin outline in the dataset colour (this is the RMS/Waveform fix).
      edge = pg.mkPen(color, width=1.0)
      c_lo = pg.PlotDataItem(band.x, lo, pen=edge)
      c_hi = pg.PlotDataItem(band.x, hi, pen=edge)
      self.plot.addItem(c_lo)
      self.plot.addItem(c_hi)
      # Build the colour with alpha up front: QBrush.color() returns a copy, so
      # mutating its alpha after mkBrush would be a no-op (opaque overlay bug).
      fill_color = pg.mkColor(color)
      fill_color.setAlpha(200 if single else 90)
      fill = pg.FillBetweenItem(c_lo, c_hi, brush=pg.mkBrush(fill_color))
      self.plot.addItem(fill)
      if band.label:
        self._legend_swatch(prefix + band.label, color)

    for curve in spec.curves:
      pen = pg.mkPen(curve.color or color, width=curve.width)
      item = self.plot.plot(curve.x, curve.y, pen=pen,
                            name=(prefix + curve.label) if curve.label else None,
                            connect="finite")  # gaps at NaN (gated PSR)
      item.setDownsampling(auto=True)  # keep big series smooth under zoom
      item.setClipToView(True)

  def _render_hline(self, hl):
    pen = pg.mkPen(hl.color, width=hl.width, style=_PEN_STYLE.get(hl.style, Qt.DotLine))
    line = pg.InfiniteLine(
      pos=hl.y, angle=0, pen=pen, movable=False,
      label=hl.label or None,
      labelOpts={"position": 0.95, "color": hl.color, "fill": (255, 255, 255, 150)},
    )
    self.plot.addItem(line)

  def _render_heatmap(self, spec: PlotSpec, view: ViewState):
    hm = spec.heatmap
    t0, t1 = float(hm.x[0]), float(hm.x[-1])
    f_lo = max(spec.axes.y_range[0] if spec.axes.y_range else hm.y[0], hm.y[0])
    f_hi = spec.axes.y_range[1] if spec.axes.y_range else hm.y[-1]
    y_log = view.resolve_y_log(default=spec.axes.y_log)

    n_rows = len(hm.y)
    if y_log:
      f_grid = np.logspace(np.log10(max(f_lo, 1e-6)), np.log10(f_hi), n_rows)
    else:
      f_grid = np.linspace(f_lo, f_hi, n_rows)

    # Resample every time column from native linear freq bins onto f_grid in one
    # vectorised pass — this runs on each redraw and lin/log toggle, so the loop
    # version would make the toggle feel laggy on long files.
    interp = interp1d(hm.y, hm.z, axis=0, bounds_error=False,
                      fill_value=(hm.z[0], hm.z[-1]), assume_sorted=True)
    z_grid = interp(f_grid).astype(np.float32)

    img = pg.ImageItem()
    img.setImage(z_grid.T, autoLevels=False)  # ImageItem wants (x, y) -> transpose
    img.setLevels((hm.z_min, hm.z_max))
    img.setColorMap(_colormap(hm.cmap))
    # Map image pixel space (time cols, freq rows) to data coords: x=time, y=row index.
    img.setRect(pg.QtCore.QRectF(t0, 0.0, t1 - t0, float(n_rows)))
    self.plot.addItem(img)

    # Label the row-index y-axis with real frequencies.
    ticks = []
    for hz in _LOG_FREQ_TICKS:
      if f_lo <= hz <= f_hi:
        row = float(np.searchsorted(f_grid, hz))
        ticks.append((row, _fmt_hz(hz)))
    self.plot.getAxis("left").setTicks([ticks])
    self.plot.setYRange(0, n_rows, padding=0)
    self.plot.setXRange(t0, t1, padding=0)

    # Place the colourbar at a fixed layout cell and link it to the image. We
    # add/remove it ourselves (rather than insert_in=) so it can't stack across
    # repeated spectrogram renders.
    self._colorbar = pg.ColorBarItem(values=(hm.z_min, hm.z_max),
                                      colorMap=_colormap(hm.cmap), label=hm.label)
    self._colorbar.setImageItem(img)
    self.glw.addItem(self._colorbar, row=0, col=1)

  def _apply_axes(self, axes, log_y_image_handled: bool = False):
    self.plot.setLabel("bottom", axes.x_label)
    self.plot.setLabel("left", axes.y_label)
    if axes.x_range:
      self.plot.setXRange(*axes.x_range, padding=0)
    if axes.y_range and not log_y_image_handled:
      self.plot.setYRange(*axes.y_range, padding=0)
    if not log_y_image_handled:
      # Curve metrics: honour log mode if a spec ever opts in (none do today).
      self.plot.setLogMode(x=axes.x_log, y=axes.y_log)

  # ---- user reference lines -----------------------------------------------

  def _draw_user_lines(self):
    """(Re)create draggable lines from the stored values, preserving positions."""
    self._remove_user_line_items()
    for idx in range(len(self._user_line_values)):
      line = pg.InfiniteLine(
        pos=self._user_line_values[idx], angle=0, movable=True,
        pen=pg.mkPen(_USER_LINE_COLOR, width=1.2, style=Qt.DashLine),
        label="{value:.2f}",
        labelOpts={"position": 0.05, "color": _USER_LINE_COLOR,
                   "fill": (255, 255, 255, 180)},
      )
      line.sigPositionChanged.connect(lambda ln, i=idx: self._on_user_line_moved(i, ln))
      self.plot.addItem(line)
      self._user_lines.append(line)

  def _on_user_line_moved(self, index: int, line: pg.InfiniteLine):
    if 0 <= index < len(self._user_line_values):
      self._user_line_values[index] = float(line.value())

  def _remove_user_line_items(self):
    for line in self._user_lines:
      self.plot.removeItem(line)
    self._user_lines.clear()

  # ---- legend / lifecycle -------------------------------------------------

  def _legend_swatch(self, name: str, color: str):
    self.legend.addItem(pg.PlotDataItem(pen=pg.mkPen(color, width=3)), name)

  def _legend_note(self, text: str):
    self.legend.addItem(pg.PlotDataItem(pen=None), text)

  def _reset_plot(self):
    self._remove_user_line_items()  # cleared from scene; values persist for redraw
    self.plot.clear()
    if self._colorbar is not None:
      try:
        self.glw.removeItem(self._colorbar)
      except Exception:
        pass
      self._colorbar = None
    self.legend.clear()
    self.plot.getAxis("left").setTicks(None)  # drop heatmap freq ticks
    self.plot.setLogMode(x=False, y=False)

  def _show_empty(self):
    text = pg.TextItem("Drop an audio file to see analysis", anchor=(0.5, 0.5),
                       color=(120, 120, 120))
    self.plot.addItem(text)
    self.plot.setXRange(0, 1)
    self.plot.setYRange(0, 1)
    text.setPos(0.5, 0.5)
    self.set_status("Ready for audio analysis...")
