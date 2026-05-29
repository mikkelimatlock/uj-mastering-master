"""
Pluggable analysis metrics.

A `Metric` knows how to compute a series from an `AudioFile` and how to render
that series into a matplotlib `Figure`. Compute is the heavy step (runs on the
worker thread); render is cheap and reruns on font / refresh.

To add a metric: subclass `Metric`, implement `compute` and `render`, and
register the instance in `METRICS` at the bottom of this file.
"""

from __future__ import annotations

import os
import warnings
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.figure import Figure
import pyloudnorm as pyln

from font_manager import safe_title
from master_core import AudioFile


class Metric(ABC):
  """A pluggable analysis metric."""

  id: str
  display_name: str

  @abstractmethod
  def compute(self, audio_file: AudioFile) -> Any:
    """Compute and return the metric's data from a loaded AudioFile.

    The returned object is cached and later passed to `render`. This is the
    heavy step and runs on the worker thread.
    """

  @abstractmethod
  def render(self, data: Any, file_path: str, figsize=(10, 4)) -> Figure:
    """Render a Figure from precomputed data. Cheap; runs on the GUI thread."""


class RMSPowerMetric(Metric):
  id = "rms_power"
  display_name = "RMS Power"

  def __init__(self, window: int = 10, hop: int = 2):
    self.window = window
    self.hop = hop

  def compute(self, audio_file: AudioFile):
    audio_file.get_energy_levels_over_time(window=self.window, hop=self.hop)
    return {
      "times": audio_file.get_times(),
      "rms_array": audio_file.rms_array,
    }

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    rms_array = data["rms_array"]

    # Adaptive colour scale: bump headroom for loud masters.
    maxpower = 0.6 if np.max(rms_array) > 0.3 else 0.3
    norm = mcolors.Normalize(vmin=0, vmax=maxpower)
    cmap = cm.autumn

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_ylim(0., maxpower)
    for i in range(len(times) - 1):
      ax.fill_between(
        times[i:i + 2], 0, rms_array[0][i],
        color=cmap(norm(rms_array[0][i])), edgecolor="none",
      )
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="RMS Power")
    ax.set_ylabel("Power")
    ax.set_xlabel("Time (seconds)")
    ax.set_title(safe_title(os.path.basename(file_path)))
    fig.tight_layout()
    return fig


class WaveformMetric(Metric):
  """Raw mono waveform with a min/max envelope downsample for plotting speed."""

  id = "waveform"
  display_name = "Waveform"

  def __init__(self, target_columns: int = 4000):
    self.target_columns = target_columns

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono
    sr = audio_file.sr
    n = len(y)
    if n <= self.target_columns:
      times = np.arange(n) / sr
      return {"times": times, "lo": y, "hi": y}

    chunk = n // self.target_columns
    trimmed = y[: chunk * self.target_columns]
    reshaped = trimmed.reshape(self.target_columns, chunk)
    lo = reshaped.min(axis=1)
    hi = reshaped.max(axis=1)
    times = (np.arange(self.target_columns) * chunk + chunk / 2) / sr
    return {"times": times, "lo": lo, "hi": hi}

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    lo = data["lo"]
    hi = data["hi"]

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.fill_between(times, lo, hi, color="#3a7ad6", linewidth=0)
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.3)
    # Fixed full-scale range with a touch of headroom for float-wav signals.
    ax.set_ylim(-1.1, 1.1)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel("Amplitude")
    ax.set_xlabel("Time (seconds)")
    ax.set_title(safe_title(os.path.basename(file_path)))
    fig.tight_layout()
    return fig


class LUFSMetric(Metric):
  """ITU-R BS.1770 loudness: short-term (3 s) time series + integrated value.

  Powered by pyloudnorm. The time series slides `meter.integrated_loudness`
  across the track because pyloudnorm doesn't expose a per-block series.
  Slightly redundant work, but the per-call cost is small.
  """

  id = "lufs"
  display_name = "LUFS"

  # Short-term as defined by EBU R128 / BS.1770: 3-second window.
  WINDOW_S = 3.0
  HOP_S = 0.5
  SILENCE_FLOOR = -70.0  # BS.1770 absolute gate

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float64, copy=False)
    sr = audio_file.sr
    meter = pyln.Meter(sr)

    # pyloudnorm warns on clipping and on too-short audio; we handle both.
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      integrated = self._safe_integrated(meter, y)

      window_n = int(self.WINDOW_S * sr)
      hop_n = int(self.HOP_S * sr)

      if len(y) < window_n:
        # Track shorter than 3 s — just one data point at the centre.
        times = np.array([len(y) / (2.0 * sr)])
        lufs = np.array([integrated if np.isfinite(integrated) else self.SILENCE_FLOOR])
      else:
        n_windows = 1 + (len(y) - window_n) // hop_n
        lufs = np.empty(n_windows)
        for i in range(n_windows):
          start = i * hop_n
          lufs[i] = self._safe_integrated(meter, y[start:start + window_n])
        times = (np.arange(n_windows) * hop_n + window_n / 2.0) / sr

    lufs = np.where(np.isfinite(lufs), lufs, self.SILENCE_FLOOR)
    lufs = np.clip(lufs, self.SILENCE_FLOOR, 0.0)

    return {
      "times": times,
      "lufs": lufs,
      "integrated": float(integrated),
    }

  @staticmethod
  def _safe_integrated(meter: "pyln.Meter", segment: np.ndarray) -> float:
    try:
      return float(meter.integrated_loudness(segment))
    except (ValueError, FloatingPointError):
      return float("-inf")

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    lufs = data["lufs"]
    integrated = data["integrated"]

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.plot(times, lufs, color="#2a9d8f", linewidth=1.4, label="Short-term (3 s)")

    if np.isfinite(integrated):
      ax.axhline(
        integrated, color="#e76f51", linestyle="--", linewidth=1.5,
        label=f"Integrated: {integrated:.1f} LUFS",
      )

    # Streaming target reference (Spotify normalises to -14 LUFS).
    ax.axhline(-14.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(
      times[-1], -14.0, "  -14 LUFS (streaming target)",
      va="center", ha="left", fontsize=8, alpha=0.6,
    )

    ax.set_ylim(-50.0, 0.0)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel("LUFS")
    ax.set_xlabel("Time (seconds)")
    ax.set_title(safe_title(os.path.basename(file_path)))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


METRICS: dict[str, Metric] = {
  m.id: m for m in (
    RMSPowerMetric(),
    WaveformMetric(),
    LUFSMetric(),
  )
}
DEFAULT_METRIC_ID = "rms_power"
