"""
Backend-agnostic plot descriptors.

A metric's `build_spec` turns precomputed data into a `PlotSpec`: a declarative
description of *what* to draw (curves, reference lines, an optional heatmap) and
*how the axes should behave* (labels, default scale, which lin/log toggles are
legal). It says nothing about the plotting library, colours, or widget layout —
that is the renderer's job.

This seam is what makes overlay/compare cheap: drawing N datasets on one axis is
"render N specs," and the renderer owns the colour cycle so overlaid curves stay
distinct. It is also what makes lin/log a pure view toggle — `build_spec` takes a
`ViewState`, so switching scale never touches `compute`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class Curve:
  """A single x/y line. Colour is assigned by the renderer for overlay distinctness."""
  x: np.ndarray
  y: np.ndarray
  label: str = ""
  width: float = 1.4
  # Explicit colour overrides the dataset colour cycle. Leave None for overlay.
  color: Optional[str] = None


@dataclass
class HLine:
  """A horizontal reference line with an attached label.

  The label rides on the line itself (renderer places it), so reference markers
  no longer need anchoring at `times[-1]` — overlaid tracks of different lengths
  stop fighting over label position.
  """
  y: float
  label: str = ""
  color: str = "#888888"
  style: str = "dot"  # 'solid' | 'dash' | 'dot'
  width: float = 0.8


@dataclass
class Band:
  """A filled envelope between `lo` and `hi` over `x` (RMS area, waveform min/max).

  One drawn primitive instead of thousands of per-segment fills, and overlay-safe:
  the renderer gives each dataset's band a translucent dataset colour.
  """
  x: np.ndarray
  lo: np.ndarray            # scalar-broadcast or per-x lower edge
  hi: np.ndarray            # per-x upper edge
  label: str = ""
  color: Optional[str] = None


@dataclass
class Heatmap:
  """A 2-D field (e.g. a spectrogram). Heatmaps do not overlay — at most one."""
  x: np.ndarray             # column axis (time)
  y: np.ndarray             # row axis (frequency), linear; renderer handles log
  z: np.ndarray             # shape (len(y), len(x))
  z_min: float
  z_max: float
  cmap: str = "magma"
  label: str = ""           # colourbar label


@dataclass
class AxisSpec:
  x_label: str = ""
  y_label: str = ""
  y_log: bool = False               # this metric's natural default scale
  x_log: bool = False
  y_range: Optional[tuple[float, float]] = None
  x_range: Optional[tuple[float, float]] = None
  y_log_allowed: bool = False       # is a lin/log toggle meaningful on this axis?
  x_log_allowed: bool = False


@dataclass
class PlotSpec:
  """Everything the renderer needs to draw one dataset of one metric."""
  title: str = ""
  axes: AxisSpec = field(default_factory=AxisSpec)
  curves: list[Curve] = field(default_factory=list)
  bands: list[Band] = field(default_factory=list)
  hlines: list[HLine] = field(default_factory=list)
  heatmap: Optional[Heatmap] = None
  # Scalar readouts (integrated LUFS, LRA, max dBTP) surfaced in the legend.
  annotations: list[str] = field(default_factory=list)

  @property
  def is_heatmap(self) -> bool:
    return self.heatmap is not None


@dataclass
class ViewState:
  """User-controlled, recompute-free view options.

  `None` means "use the metric's default for this axis." `build_spec` resolves
  the concrete scale via `resolve_*`, so a metric never has to special-case the
  unset state.
  """
  y_log: Optional[bool] = None
  x_log: Optional[bool] = None

  def resolve_y_log(self, default: bool) -> bool:
    return self.y_log if self.y_log is not None else default

  def resolve_x_log(self, default: bool) -> bool:
    return self.x_log if self.x_log is not None else default


# A neutral default reused wherever a caller hasn't supplied view options.
DEFAULT_VIEW = ViewState()
