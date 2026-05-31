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
from scipy import signal as scipy_signal

from font_manager import safe_title
from master_core import AudioFile


# Small constant to keep 20*log10(...) from blowing up on perfect silence.
_EPS = 1e-12


def _to_dbfs(linear: np.ndarray | float) -> np.ndarray | float:
  """Convert a linear magnitude to dBFS, floored at _EPS."""
  return 20.0 * np.log10(np.maximum(linear, _EPS))


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
  """ITU-R BS.1770 loudness: short-term (3 s) time series + integrated + LRA.

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

    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      integrated = self._safe_integrated(meter, y)

      window_n = int(self.WINDOW_S * sr)
      hop_n = int(self.HOP_S * sr)

      if len(y) < window_n:
        times = np.array([len(y) / (2.0 * sr)])
        lufs = np.array([integrated if np.isfinite(integrated) else self.SILENCE_FLOOR])
        lra = float("nan")
      else:
        n_windows = 1 + (len(y) - window_n) // hop_n
        lufs = np.empty(n_windows)
        for i in range(n_windows):
          start = i * hop_n
          lufs[i] = self._safe_integrated(meter, y[start:start + window_n])
        times = (np.arange(n_windows) * hop_n + window_n / 2.0) / sr
        try:
          lra = float(meter.loudness_range(y))
        except (ValueError, FloatingPointError):
          lra = float("nan")

    lufs = np.where(np.isfinite(lufs), lufs, self.SILENCE_FLOOR)
    lufs = np.clip(lufs, self.SILENCE_FLOOR, 0.0)

    return {
      "times": times,
      "lufs": lufs,
      "integrated": float(integrated),
      "lra": lra,
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
    lra = data.get("lra", float("nan"))

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.plot(times, lufs, color="#2a9d8f", linewidth=1.4, label="Short-term (3 s)")

    if np.isfinite(integrated):
      ax.axhline(
        integrated, color="#e76f51", linestyle="--", linewidth=1.5,
        label=f"Integrated: {integrated:.1f} LUFS",
      )

    if np.isfinite(lra):
      # Invisible plot entry to surface LRA in the legend without adding a line.
      ax.plot([], [], " ", label=f"LRA: {lra:.1f} LU")

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


class CrestFactorMetric(Metric):
  """Crest factor = 20*log10(peak / RMS) per sliding window, in dB."""

  id = "crest_factor"
  display_name = "Crest Factor"

  WINDOW_S = 1.0
  HOP_S = 0.25

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float64, copy=False)
    sr = audio_file.sr
    window_n = int(self.WINDOW_S * sr)
    hop_n = int(self.HOP_S * sr)

    if len(y) < window_n:
      times = np.array([len(y) / (2.0 * sr)])
      peak = float(np.max(np.abs(y))) if len(y) else 0.0
      rms = float(np.sqrt(np.mean(y * y))) if len(y) else 0.0
      crest = 20.0 * np.log10(max(peak, _EPS) / max(rms, _EPS))
      return {"times": times, "crest_db": np.array([crest])}

    # RMS via cumulative-sum-of-squares (O(N)); peaks via sliding window view.
    y2 = y * y
    cumsum = np.concatenate(([0.0], np.cumsum(y2)))
    n_windows = 1 + (len(y) - window_n) // hop_n
    starts = np.arange(n_windows) * hop_n
    ends = starts + window_n
    mean_sq = (cumsum[ends] - cumsum[starts]) / window_n
    rms = np.sqrt(np.maximum(mean_sq, _EPS))

    abs_y = np.abs(y)
    peaks = np.empty(n_windows)
    for i in range(n_windows):
      peaks[i] = np.max(abs_y[starts[i]:ends[i]])

    crest_db = 20.0 * np.log10(np.maximum(peaks, _EPS) / rms)
    times = (starts + window_n / 2.0) / sr
    return {"times": times, "crest_db": crest_db}

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    crest_db = data["crest_db"]

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.plot(times, crest_db, color="#e09f3e", linewidth=1.4, label=f"Crest factor (1 s)")

    # Rules of thumb: ~12 dB = roomy, ~6 dB = heavily limited.
    ax.axhline(12.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(times[-1], 12.0, "  12 dB", va="center", ha="left", fontsize=8, alpha=0.6)
    ax.axhline(6.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(times[-1], 6.0, "  6 dB (squashed)", va="center", ha="left", fontsize=8, alpha=0.6)

    ax.set_ylim(0.0, 25.0)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel("Crest factor (dB)")
    ax.set_xlabel("Time (seconds)")
    ax.set_title(safe_title(os.path.basename(file_path)))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


class PSRMetric(Metric):
  """Peak-to-Short-term LUFS Ratio (sample-peak variant), in LU.

  PSR = sample_peak_dBFS - short_term_LUFS  over the same 3 s windows used by
  LUFSMetric. High PSR = punchy transients; low PSR = heavily limited.
  """

  id = "psr"
  display_name = "PSR"

  WINDOW_S = 3.0
  HOP_S = 0.5
  SILENCE_FLOOR = -70.0

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float64, copy=False)
    sr = audio_file.sr
    meter = pyln.Meter(sr)

    window_n = int(self.WINDOW_S * sr)
    hop_n = int(self.HOP_S * sr)

    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      if len(y) < window_n:
        times = np.array([len(y) / (2.0 * sr)])
        peak_db = _to_dbfs(np.max(np.abs(y))) if len(y) else self.SILENCE_FLOOR
        lufs = LUFSMetric._safe_integrated(meter, y)
        psr = peak_db - lufs if np.isfinite(lufs) else 0.0
        return {"times": times, "psr": np.array([psr])}

      n_windows = 1 + (len(y) - window_n) // hop_n
      abs_y = np.abs(y)
      lufs_series = np.empty(n_windows)
      peaks_db = np.empty(n_windows)
      for i in range(n_windows):
        start = i * hop_n
        end = start + window_n
        peaks_db[i] = _to_dbfs(np.max(abs_y[start:end]))
        lufs_series[i] = LUFSMetric._safe_integrated(meter, y[start:end])
      times = (np.arange(n_windows) * hop_n + window_n / 2.0) / sr

    # PSR is meaningless where the loudness reading is below the absolute gate.
    valid = np.isfinite(lufs_series) & (lufs_series > self.SILENCE_FLOOR)
    psr = np.where(valid, peaks_db - lufs_series, np.nan)
    return {"times": times, "psr": psr}

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    psr = data["psr"]

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.plot(times, psr, color="#7251b5", linewidth=1.4, label="PSR (3 s)")

    # Ian Shepherd's rough thresholds.
    ax.axhline(10.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(times[-1], 10.0, "  10 LU (good punch)", va="center", ha="left", fontsize=8, alpha=0.6)
    ax.axhline(4.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(times[-1], 4.0, "  4 LU (squashed)", va="center", ha="left", fontsize=8, alpha=0.6)

    ax.set_ylim(0.0, 25.0)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel("PSR (LU)")
    ax.set_xlabel("Time (seconds)")
    ax.set_title(safe_title(os.path.basename(file_path)))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


class TruePeakMetric(Metric):
  """ITU-R BS.1770 true peak via 4x polyphase oversampling, in dBTP.

  Per-window true peak with a moderate hop so it renders quickly. Windows are
  oversampled independently — slight edge under-detection at window boundaries
  is masked by the 60% overlap.
  """

  id = "true_peak"
  display_name = "True Peak"

  WINDOW_S = 0.25
  HOP_S = 0.1
  OVERSAMPLE = 4

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float32, copy=False)
    sr = audio_file.sr
    window_n = int(self.WINDOW_S * sr)
    hop_n = int(self.HOP_S * sr)

    if len(y) < window_n:
      y_up = scipy_signal.resample_poly(y, self.OVERSAMPLE, 1) if len(y) else np.zeros(1, dtype=np.float32)
      peak_db = _to_dbfs(np.max(np.abs(y_up))) if len(y_up) else -70.0
      return {
        "times": np.array([len(y) / (2.0 * sr)]),
        "tp_db": np.array([peak_db]),
        "integrated_tp_db": float(peak_db),
      }

    n_windows = 1 + (len(y) - window_n) // hop_n
    tp_db = np.empty(n_windows)
    for i in range(n_windows):
      start = i * hop_n
      w = y[start:start + window_n]
      w_up = scipy_signal.resample_poly(w, self.OVERSAMPLE, 1)
      tp_db[i] = _to_dbfs(np.max(np.abs(w_up)))
    times = (np.arange(n_windows) * hop_n + window_n / 2.0) / sr

    integrated_tp_db = float(np.max(tp_db))
    return {"times": times, "tp_db": tp_db, "integrated_tp_db": integrated_tp_db}

  def render(self, data, file_path, figsize=(10, 4)) -> Figure:
    times = data["times"]
    tp_db = data["tp_db"]
    integrated = data.get("integrated_tp_db", float("nan"))

    fig = Figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    ax.plot(times, tp_db, color="#c1121f", linewidth=1.0, label="True Peak (250 ms)")

    # 0 dBTP = sample-level clip; -1 dBTP a common mastering ceiling.
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.text(times[-1], 0.0, "  0 dBTP (clip)", va="center", ha="left", fontsize=8, alpha=0.7)
    ax.axhline(-1.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.text(times[-1], -1.0, "  -1 dBTP (typical ceiling)", va="center", ha="left", fontsize=8, alpha=0.6)

    if np.isfinite(integrated):
      ax.plot([], [], " ", label=f"Max: {integrated:.2f} dBTP")

    ax.set_ylim(-30.0, 6.0)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel("dBTP")
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
    CrestFactorMetric(),
    PSRMetric(),
    TruePeakMetric(),
  )
}
DEFAULT_METRIC_ID = "rms_power"
