"""
Analysis Results Manager - Bridge between audio processing and GUI.
Manages analysis queue and coordinates between components.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread
from dataclasses import dataclass, field
from typing import Any, Optional
import os
import logging

from master_core import AudioFile
from font_manager import safe_title
from metrics import METRICS, DEFAULT_METRIC_ID, Metric


@dataclass
class AnalysisResult:
  """Container for audio analysis results."""
  file_path: str
  audio_file: AudioFile
  song_name: str
  max_amplitude: float
  avg_amplitude: float
  metric_data: dict[str, Any] = field(default_factory=dict)
  analysis_successful: bool = True
  error_message: str = ""

  def metadata_text(self) -> str:
    return (
      f"Track: {safe_title(self.song_name)}\n"
      f"Max Amplitude: {self.max_amplitude:.3f}\n"
      f"Avg Amplitude: {self.avg_amplitude:.3f}"
    )


class AudioAnalysisWorker(QThread):
  """Worker thread that loads audio and computes a single metric."""

  progressUpdate = pyqtSignal(str, int)  # message, percentage
  analysisCompleted = pyqtSignal(str, object)  # file_path, AnalysisResult
  analysisError = pyqtSignal(str, str)  # file_path, error_message

  def __init__(self, file_path: str, metric: Metric):
    super().__init__()
    self.file_path = file_path
    self.metric = metric
    self.logger = logging.getLogger(__name__)

  def run(self):
    try:
      self.logger.info(f"Starting analysis of: {os.path.basename(self.file_path)}")
      self.progressUpdate.emit("Loading audio file...", 10)

      audio_file = AudioFile(self.file_path)
      self.progressUpdate.emit("Audio loaded...", 30)

      self.progressUpdate.emit(f"Computing {self.metric.display_name}...", 60)
      metric_data = {self.metric.id: self.metric.compute(audio_file)}

      self.progressUpdate.emit("Finalizing analysis...", 90)

      result = AnalysisResult(
        file_path=self.file_path,
        audio_file=audio_file,
        song_name=audio_file.song_name,
        max_amplitude=audio_file.max_amplitude,
        avg_amplitude=audio_file.avg_amplitude,
        metric_data=metric_data,
        analysis_successful=True,
      )

      self.progressUpdate.emit("Analysis complete!", 100)
      self.logger.info(f"Analysis completed: {os.path.basename(self.file_path)}")
      self.analysisCompleted.emit(self.file_path, result)

    except Exception as e:
      error_msg = f"Analysis failed: {str(e)}"
      self.logger.error(f"Analysis error for {self.file_path}: {error_msg}")
      self.analysisError.emit(self.file_path, error_msg)


class MetricComputeWorker(QThread):
  """Worker thread that computes a single metric against an already-loaded AudioFile."""

  completed = pyqtSignal(str, str, object)  # file_path, metric_id, data
  failed = pyqtSignal(str, str, str)         # file_path, metric_id, error_message

  def __init__(self, file_path: str, audio_file: AudioFile, metric: Metric):
    super().__init__()
    self.file_path = file_path
    self.audio_file = audio_file
    self.metric = metric
    self.logger = logging.getLogger(__name__)

  def run(self):
    try:
      self.logger.info(
        f"Computing {self.metric.display_name} for {os.path.basename(self.file_path)}"
      )
      data = self.metric.compute(self.audio_file)
      self.completed.emit(self.file_path, self.metric.id, data)
    except Exception as e:
      msg = f"{self.metric.display_name} compute failed: {e}"
      self.logger.error(msg)
      self.failed.emit(self.file_path, self.metric.id, str(e))


class AnalysisResultsManager(QObject):
  """Manages audio file analysis and coordinates between processing and GUI."""

  # Full-analysis (load + initial metric) signals.
  analysisStarted = pyqtSignal(str)
  analysisCompleted = pyqtSignal(str, object)
  analysisError = pyqtSignal(str, str)
  progressUpdate = pyqtSignal(str, int)

  # Metric-only signals (used for switches after analysis has completed).
  metricComputeStarted = pyqtSignal(str, str)   # file_path, metric_id
  metricReady = pyqtSignal(str, str)            # file_path, metric_id
  metricComputeError = pyqtSignal(str, str, str)  # file_path, metric_id, error

  def __init__(self):
    super().__init__()
    self.results_cache: dict[str, AnalysisResult] = {}
    self.current_worker: Optional[AudioAnalysisWorker] = None
    self.metric_workers: dict[tuple[str, str], MetricComputeWorker] = {}
    self.logger = logging.getLogger(__name__)

  def analyze_file(self, file_path: str, metric_id: str = DEFAULT_METRIC_ID):
    """Kick off background analysis for the given file and metric."""
    if not os.path.exists(file_path):
      error_msg = f"File not found: {file_path}"
      self.logger.error(error_msg)
      self.analysisError.emit(file_path, error_msg)
      return

    metric = METRICS.get(metric_id)
    if metric is None:
      error_msg = f"Unknown metric: {metric_id}"
      self.logger.error(error_msg)
      self.analysisError.emit(file_path, error_msg)
      return

    if self.current_worker and self.current_worker.isRunning():
      self.logger.info("Stopping previous analysis to start new one")
      self.current_worker.quit()
      self.current_worker.wait()

    self.analysisStarted.emit(file_path)
    self.logger.info(
      f"Queuing analysis: {os.path.basename(file_path)} ({metric.display_name})"
    )

    self.current_worker = AudioAnalysisWorker(file_path, metric)
    self.current_worker.progressUpdate.connect(self.progressUpdate.emit)
    self.current_worker.analysisCompleted.connect(self._on_worker_completed)
    self.current_worker.analysisError.connect(self.analysisError.emit)
    self.current_worker.start()

  def _on_worker_completed(self, file_path: str, result: AnalysisResult):
    self.results_cache[file_path] = result
    self.analysisCompleted.emit(file_path, result)

  def request_metric(self, file_path: str, metric_id: str) -> bool:
    """Ensure the metric's data exists for the file; emit metricReady when ready.

    Returns True if the data was already cached (metricReady emitted synchronously)
    or successfully kicked off (will emit later). Returns False if the file hasn't
    been analysed yet or the metric id is unknown — in that case the caller
    should wait for analysisCompleted or correct the metric id.
    """
    result = self.results_cache.get(file_path)
    if result is None:
      return False

    metric = METRICS.get(metric_id)
    if metric is None:
      self.logger.warning(f"Unknown metric requested: {metric_id}")
      return False

    if metric_id in result.metric_data:
      # Cached — emit immediately so the caller can re-render.
      self.metricReady.emit(file_path, metric_id)
      return True

    key = (file_path, metric_id)
    existing = self.metric_workers.get(key)
    if existing is not None and existing.isRunning():
      self.logger.debug(f"Metric compute already in flight: {metric_id} for {os.path.basename(file_path)}")
      return True

    worker = MetricComputeWorker(file_path, result.audio_file, metric)
    worker.completed.connect(self._on_metric_completed)
    worker.failed.connect(self._on_metric_failed)
    self.metric_workers[key] = worker
    self.metricComputeStarted.emit(file_path, metric_id)
    worker.start()
    return True

  def _on_metric_completed(self, file_path: str, metric_id: str, data: object):
    result = self.results_cache.get(file_path)
    if result is not None:
      result.metric_data[metric_id] = data
    self.metric_workers.pop((file_path, metric_id), None)
    self.metricReady.emit(file_path, metric_id)

  def _on_metric_failed(self, file_path: str, metric_id: str, error_message: str):
    self.metric_workers.pop((file_path, metric_id), None)
    self.metricComputeError.emit(file_path, metric_id, error_message)

  def get_metric_data(self, file_path: str, metric_id: str):
    """Return cached metric data, or None if not computed yet.

    Never triggers compute — call `request_metric` first and listen for
    `metricReady` if you need on-demand computation. Spec/figure building is the
    GUI layer's job (it owns the view-state), so this stays render-agnostic.
    """
    result = self.results_cache.get(file_path)
    if result is None:
      return None
    if metric_id not in METRICS:
      return None
    return result.metric_data.get(metric_id)

  def display_label(self, file_path: str) -> str:
    """Short human label for a file (song name if known, else basename)."""
    result = self.results_cache.get(file_path)
    if result is not None and result.song_name:
      return result.song_name
    return os.path.basename(file_path)

  def get_metadata_text(self, file_path: str) -> str:
    result = self.results_cache.get(file_path)
    if result is None:
      return "No analysis data available"
    return result.metadata_text()

  def clear_cache(self):
    self.results_cache.clear()

  def is_file_analyzed(self, file_path: str) -> bool:
    return file_path in self.results_cache
