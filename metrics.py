"""
Pluggable analysis metrics.

A `Metric` computes a backend-neutral data object from an `AudioFile` and then
turns that data into a `PlotSpec` (declarative drawing intent). Compute is the
heavy step and runs on the worker thread; `build_spec` is cheap, view-aware, and
reruns on every scale toggle / overlay change without recomputation.

To add a metric: subclass `Metric`, implement `compute` and `build_spec`, and
register the instance in `METRICS` at the bottom of this file.

Note: metrics no longer touch matplotlib or know which library draws them. The
old `_show_axis_extents` endpoint-labelling lived in the matplotlib render path
and is gone for now; if exact-extent tick labels are wanted back, they belong in
the renderer, applied uniformly to every metric.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import librosa
import pyloudnorm as pyln
from scipy import signal as scipy_signal
from scipy.ndimage import maximum_filter1d

from master_core import AudioFile
from plotspec import (
  AxisSpec, Band, Curve, Heatmap, HLine, PlotSpec, ViewState, DEFAULT_VIEW,
)


# Small constant to keep 20*log10(...) from blowing up on perfect silence.
_EPS = 1e-12


def _to_dbfs(linear: np.ndarray | float) -> np.ndarray | float:
  """Convert a linear magnitude to dBFS, floored at _EPS."""
  return 20.0 * np.log10(np.maximum(linear, _EPS))


def _window_starts(n: int, window_n: int, hop_n: int) -> np.ndarray:
  """Start indices of every full sliding window of length `window_n` over `n`."""
  n_windows = 1 + (n - window_n) // hop_n
  return np.arange(n_windows) * hop_n


def _window_peaks(abs_signal: np.ndarray, starts: np.ndarray, window_n: int) -> np.ndarray:
  """Max of `abs_signal` over each window [start, start+window_n), vectorised.

  Uses an O(N) running-max (scipy maximum_filter1d) sampled at window centres,
  replacing the per-window Python `np.max` loops. `maximum_filter1d` centres a
  size-`window_n` window on each index, so the centre of [start, start+window_n)
  is `start + window_n//2` — the two line up exactly for even windows.
  """
  running = maximum_filter1d(abs_signal, size=window_n)
  centers = np.minimum(starts + window_n // 2, len(abs_signal) - 1)
  return running[centers]


# BS.1770 loudness offset and absolute gate, shared by the routines below.
_LUFS_OFFSET = -0.691
_ABS_GATE = -70.0


def _kweight(audio_file: AudioFile) -> np.ndarray:
  """K-weighted mono signal (float64), filtered once and cached on the AudioFile.

  Uses pyloudnorm's own BS.1770 biquad coefficients and filtering (passband_gain
  * lfilter, exactly as `IIRfilter.apply_filter`), so every loudness quantity
  derived from it matches pyloudnorm. Depends on `Meter._filters` internals; the
  dev-time validation guards against a coefficient change.
  """
  cached = getattr(audio_file, "_yk", None)
  if cached is not None:
    return cached
  yk = audio_file.y_mono.astype(np.float64, copy=False)
  for filt in pyln.Meter(audio_file.sr)._filters.values():
    yk = filt.passband_gain * scipy_signal.lfilter(filt.b, filt.a, yk)
  audio_file._yk = yk
  return yk


def _block_loudness(yk: np.ndarray, sr: int, block_s: float, step_pct: float):
  """Per-block mean-square energy `z` and block loudness `l`, matching pyloudnorm.

  Blocks are `block_s` long, stepped by `block_s * step_pct`; energy is divided
  by the *nominal* block length (not the rounded sample count), exactly as
  BS.1770 / pyloudnorm define it.
  """
  T = len(yk) / sr
  n_blocks = int(np.round((T - block_s) / (block_s * step_pct)) + 1)
  if n_blocks < 1:
    return np.array([]), np.array([])
  j = np.arange(n_blocks)
  lo = (block_s * (j * step_pct) * sr).astype(int)
  up = np.minimum((block_s * (j * step_pct + 1) * sr).astype(int), len(yk))
  csq = np.concatenate(([0.0], np.cumsum(yk * yk)))
  z = (csq[up] - csq[lo]) / (block_s * sr)
  with np.errstate(divide="ignore"):
    l = _LUFS_OFFSET + 10.0 * np.log10(z)
  return z, l


def _integrated_lufs(yk: np.ndarray, sr: int) -> float:
  """ITU-R BS.1770 integrated (two-stage gated) loudness from the K-weighted signal.

  Reimplements pyloudnorm's gating on 400 ms / 75%-overlap blocks — validated
  bit-equal to `Meter.integrated_loudness` — so the whole-signal re-filter that
  pyloudnorm would do is avoided (the K-weighting is already cached).
  """
  z, l = _block_loudness(yk, sr, block_s=0.4, step_pct=0.25)
  abs_gated = l >= _ABS_GATE
  if not abs_gated.any():
    return float("-inf")
  gamma_r = _LUFS_OFFSET + 10.0 * np.log10(np.mean(z[abs_gated])) - 10.0
  gated = (l > gamma_r) & (l > _ABS_GATE)
  if not gated.any():
    return float("-inf")
  return float(_LUFS_OFFSET + 10.0 * np.log10(np.mean(z[gated])))


def _loudness_range(yk: np.ndarray, sr: int) -> float:
  """EBU Tech 3342 loudness range (LU) from the K-weighted signal.

  3 s blocks at ~10 Hz with 1.5 s of trailing silence, absolute + relative
  gating, then the 95th-minus-10th percentile spread — matching pyloudnorm's
  `loudness_range` (validated bit-equal).
  """
  yk_padded = np.concatenate((yk, np.zeros(int(1.5 * sr))))
  _, l = _block_loudness(yk_padded, sr, block_s=3.0, step_pct=0.03)
  abs_gated = l[l >= _ABS_GATE]
  if len(abs_gated) == 0:
    return float("nan")
  stl_integrated = 10.0 * np.log10(np.mean(np.power(10.0, abs_gated / 10.0)))
  rel_gated = abs_gated[abs_gated >= stl_integrated - 20.0]
  if len(rel_gated) == 0:
    return float("nan")
  return float(np.percentile(rel_gated, 95) - np.percentile(rel_gated, 10))


def _short_term_lufs(audio_file: AudioFile, window_s: float, hop_s: float):
  """True (ungated) EBU R128 short-term loudness series + window-centre times.

  A vectorised sliding mean-square over the cached K-weighted signal — ~8x faster
  than the old loop of per-window `integrated_loudness` calls, which also wrongly
  gated each 3 s window (short-term loudness is ungated by definition).

  Memoised on the AudioFile so LUFS and PSR (same 3 s / 0.5 s window) share it.
  """
  key = (round(window_s, 6), round(hop_s, 6))
  cache = getattr(audio_file, "_st_lufs_cache", None)
  if cache is None:
    cache = audio_file._st_lufs_cache = {}
  if key in cache:
    return cache[key]

  yk = _kweight(audio_file)
  sr = audio_file.sr
  n = len(yk)
  window_n = max(int(window_s * sr), 1)
  hop_n = max(int(hop_s * sr), 1)
  if n < window_n:
    ms = float(np.mean(yk * yk)) if n else 0.0
    times = np.array([n / (2.0 * sr)])
    lufs = np.array([_LUFS_OFFSET + 10.0 * np.log10(max(ms, _EPS))])
  else:
    csq = np.concatenate(([0.0], np.cumsum(yk * yk)))
    starts = _window_starts(n, window_n, hop_n)
    ms = (csq[starts + window_n] - csq[starts]) / window_n
    lufs = _LUFS_OFFSET + 10.0 * np.log10(np.maximum(ms, _EPS))
    times = (starts + window_n / 2.0) / sr

  cache[key] = (times, lufs)
  return cache[key]


class Metric(ABC):
  """A pluggable analysis metric."""

  id: str
  display_name: str

  @abstractmethod
  def compute(self, audio_file: AudioFile) -> Any:
    """Compute and return the metric's data from a loaded AudioFile.

    The returned object must be backend-neutral (numpy arrays + scalars). It is
    cached and later passed to `build_spec`. Heavy; runs on the worker thread.
    """

  @abstractmethod
  def build_spec(self, data: Any, view: ViewState = DEFAULT_VIEW) -> PlotSpec:
    """Turn precomputed data into a PlotSpec. Cheap; runs on the GUI thread.

    `view` carries recompute-free options (lin/log). Titles are set by the
    renderer per dataset, not here, so specs compose under overlay.
    """


class RMSPowerMetric(Metric):
  """Rolling RMS power as a filled area over time."""

  id = "rms_power"
  display_name = "RMS Power"

  def __init__(self, window: int = 10, hop: int = 2):
    self.window = window
    self.hop = hop

  def compute(self, audio_file: AudioFile):
    audio_file.get_energy_levels_over_time(window=self.window, hop=self.hop)
    return {
      "times": audio_file.get_times(),
      "rms": np.asarray(audio_file.rms_array).reshape(-1),
    }

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    rms = data["rms"]
    # Adaptive headroom: loud masters get a taller scale.
    ymax = 0.6 if (rms.size and np.max(rms) > 0.3) else 0.3
    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="Power",
        y_range=(0.0, ymax),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      bands=[Band(x=times, lo=np.zeros_like(rms), hi=rms, label="RMS power")],
    )


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

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="Amplitude",
        y_range=(-1.1, 1.1),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      bands=[Band(x=times, lo=data["lo"], hi=data["hi"], label="Waveform")],
    )


class LUFSMetric(Metric):
  """ITU-R BS.1770 loudness: short-term (3 s) time series + integrated + LRA."""

  id = "lufs"
  display_name = "LUFS"

  WINDOW_S = 3.0
  HOP_S = 0.5
  SILENCE_FLOOR = -70.0  # BS.1770 absolute gate

  def compute(self, audio_file: AudioFile):
    sr = audio_file.sr

    # Short-term series: fast, ungated, shared with PSR.
    times, lufs = _short_term_lufs(audio_file, self.WINDOW_S, self.HOP_S)
    lufs = np.clip(np.where(np.isfinite(lufs), lufs, self.SILENCE_FLOOR),
                   self.SILENCE_FLOOR, 0.0)

    # Integrated + LRA from the same cached K-weighting (gating matches pyloudnorm).
    yk = _kweight(audio_file)
    integrated = _integrated_lufs(yk, sr)
    lra = _loudness_range(yk, sr) if len(yk) >= int(self.WINDOW_S * sr) else float("nan")

    return {
      "times": times,
      "lufs": lufs,
      "integrated": float(integrated),
      "lra": lra,
    }

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    lufs = data["lufs"]
    integrated = data["integrated"]
    lra = data.get("lra", float("nan"))

    hlines = [
      HLine(y=-14.0, label="-14 LUFS (streaming target)", style="dot"),
    ]
    annotations = []
    if np.isfinite(integrated):
      hlines.append(HLine(y=integrated, label=f"Integrated: {integrated:.1f} LUFS",
                          color="#e76f51", style="dash", width=1.5))
    if np.isfinite(lra):
      annotations.append(f"LRA: {lra:.1f} LU")

    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="LUFS",
        y_range=(-50.0, 0.0),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      curves=[Curve(x=times, y=lufs, label="Short-term (3 s)")],
      hlines=hlines,
      annotations=annotations,
    )


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

    # RMS via cumulative-sum-of-squares (O(N)); peaks via O(N) running max.
    y2 = y * y
    cumsum = np.concatenate(([0.0], np.cumsum(y2)))
    starts = _window_starts(len(y), window_n, hop_n)
    mean_sq = (cumsum[starts + window_n] - cumsum[starts]) / window_n
    rms = np.sqrt(np.maximum(mean_sq, _EPS))

    peaks = _window_peaks(np.abs(y), starts, window_n)

    crest_db = 20.0 * np.log10(np.maximum(peaks, _EPS) / rms)
    times = (starts + window_n / 2.0) / sr
    return {"times": times, "crest_db": crest_db}

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="Crest factor (dB)",
        y_range=(0.0, 25.0),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      curves=[Curve(x=times, y=data["crest_db"], label="Crest factor (1 s)")],
      hlines=[
        HLine(y=12.0, label="12 dB", style="dot"),
        HLine(y=6.0, label="6 dB (squashed)", style="dot"),
      ],
    )


class PSRMetric(Metric):
  """Peak-to-Short-term LUFS Ratio (sample-peak variant), in LU."""

  id = "psr"
  display_name = "PSR"

  WINDOW_S = 3.0
  HOP_S = 0.5
  SILENCE_FLOOR = -70.0

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float64, copy=False)
    sr = audio_file.sr
    window_n = max(int(self.WINDOW_S * sr), 1)
    hop_n = max(int(self.HOP_S * sr), 1)

    # Short-term loudness series, shared (cache hit) with LUFSMetric.
    times, lufs_series = _short_term_lufs(audio_file, self.WINDOW_S, self.HOP_S)
    abs_y = np.abs(y)

    if len(y) < window_n:
      peaks_db = np.array([_to_dbfs(np.max(abs_y)) if len(y) else self.SILENCE_FLOOR])
    else:
      starts = _window_starts(len(y), window_n, hop_n)
      peaks_db = _to_dbfs(_window_peaks(abs_y, starts, window_n))

    # PSR is meaningless where the loudness reading is below the absolute gate.
    valid = np.isfinite(lufs_series) & (lufs_series > self.SILENCE_FLOOR)
    psr = np.where(valid, peaks_db - lufs_series, np.nan)
    return {"times": times, "psr": psr}

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="PSR (LU)",
        y_range=(0.0, 25.0),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      curves=[Curve(x=times, y=data["psr"], label="PSR (3 s)")],
      hlines=[
        HLine(y=10.0, label="10 LU (good punch)", style="dot"),
        HLine(y=4.0, label="4 LU (squashed)", style="dot"),
      ],
    )


class TruePeakMetric(Metric):
  """ITU-R BS.1770 true peak via 4x polyphase oversampling, in dBTP."""

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

    # Oversample the whole signal once (not per window), then take an O(N)
    # running max over the oversampled windows — replaces thousands of tiny
    # resample_poly calls with one big one.
    os_factor = self.OVERSAMPLE
    abs_up = np.abs(scipy_signal.resample_poly(y, os_factor, 1).astype(np.float32))
    win_up = window_n * os_factor
    running = maximum_filter1d(abs_up, size=win_up)

    starts = _window_starts(len(y), window_n, hop_n)
    centers_up = np.minimum(starts * os_factor + win_up // 2, len(abs_up) - 1)
    tp_db = _to_dbfs(running[centers_up])
    times = (starts + window_n / 2.0) / sr

    integrated_tp_db = float(np.max(tp_db))
    return {"times": times, "tp_db": tp_db, "integrated_tp_db": integrated_tp_db}

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    times = data["times"]
    integrated = data.get("integrated_tp_db", float("nan"))
    annotations = []
    if np.isfinite(integrated):
      annotations.append(f"Max: {integrated:.2f} dBTP")
    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="dBTP",
        y_range=(-30.0, 6.0),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      curves=[Curve(x=times, y=data["tp_db"], label="True Peak (250 ms)", width=1.0)],
      hlines=[
        HLine(y=0.0, label="0 dBTP (clip)", color="#000000", style="dash", width=1.0),
        HLine(y=-1.0, label="-1 dBTP (typical ceiling)", style="dot"),
      ],
      annotations=annotations,
    )


class SpectrogramMetric(Metric):
  """Log-frequency STFT spectrogram: frequency power distribution over time."""

  id = "spectrogram"
  display_name = "Spectrogram"

  N_FFT = 4096
  TARGET_COLUMNS = 4000
  DB_FLOOR = -80.0
  F_MIN = 20.0  # log axis can't show DC; clip the low edge here

  def compute(self, audio_file: AudioFile):
    y = audio_file.y_mono.astype(np.float32, copy=False)
    sr = audio_file.sr

    min_hop = self.N_FFT // 4
    hop = max(min_hop, len(y) // self.TARGET_COLUMNS)

    stft = librosa.stft(y, n_fft=self.N_FFT, hop_length=hop)
    mag = np.abs(stft)
    s_db = librosa.amplitude_to_db(mag, ref=np.max)

    freqs = librosa.fft_frequencies(sr=sr, n_fft=self.N_FFT)
    times = librosa.frames_to_time(
        np.arange(s_db.shape[1]), sr=sr, hop_length=hop, n_fft=self.N_FFT
    )

    # Drop the DC bin (0 Hz) so a log frequency axis has no non-positive coord.
    return {
      "freqs": freqs[1:],
      "times": times,
      "s_db": s_db[1:, :],
      "nyquist": sr / 2.0,
    }

  def build_spec(self, data, view=DEFAULT_VIEW) -> PlotSpec:
    freqs = data["freqs"]
    times = data["times"]
    nyquist = data["nyquist"]
    y_log = view.resolve_y_log(default=True)  # log frequency by default

    return PlotSpec(
      axes=AxisSpec(
        x_label="Time (seconds)", y_label="Frequency (Hz)",
        y_log=y_log, y_log_allowed=True,
        y_range=(self.F_MIN, float(nyquist)),
        x_range=(float(times[0]), float(times[-1])) if times.size else None,
      ),
      heatmap=Heatmap(
        x=times, y=freqs, z=data["s_db"],
        z_min=self.DB_FLOOR, z_max=0.0, cmap="magma", label="Power (dB)",
      ),
    )


METRICS: dict[str, Metric] = {
  m.id: m for m in (
    RMSPowerMetric(),
    WaveformMetric(),
    LUFSMetric(),
    CrestFactorMetric(),
    PSRMetric(),
    TruePeakMetric(),
    SpectrogramMetric(),
  )
}
DEFAULT_METRIC_ID = "rms_power"
