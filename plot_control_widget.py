"""
Plot control widget: pick which metric to display and refresh the current plot.

Mirrors FontControlWidget's clustered-groupbox style so the two sit naturally
next to each other in the left panel.
"""

import logging
from PyQt5.QtWidgets import (
  QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox,
)
from PyQt5.QtCore import pyqtSignal

from metrics import METRICS, DEFAULT_METRIC_ID


class PlotControlWidget(QWidget):
  """Metric selector + manual plot refresh."""

  metricChanged = pyqtSignal(str)        # metric_id
  plotRefreshRequested = pyqtSignal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self.logger = logging.getLogger(__name__)
    self.initUI()

  def initUI(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(5, 5, 5, 5)

    group_box = QGroupBox("Plot")
    group_layout = QVBoxLayout(group_box)

    group_layout.addWidget(QLabel("Metric:"))
    self.metric_combo = QComboBox()
    for metric_id, metric in METRICS.items():
      self.metric_combo.addItem(metric.display_name, metric_id)
    default_idx = self.metric_combo.findData(DEFAULT_METRIC_ID)
    if default_idx >= 0:
      self.metric_combo.setCurrentIndex(default_idx)
    self.metric_combo.currentIndexChanged.connect(self._on_metric_changed)
    group_layout.addWidget(self.metric_combo)

    button_row = QHBoxLayout()
    self.refresh_button = QPushButton("Refresh Plot")
    self.refresh_button.setToolTip("Re-render the current plot with current settings")
    self.refresh_button.clicked.connect(self.plotRefreshRequested.emit)
    button_row.addWidget(self.refresh_button)
    group_layout.addLayout(button_row)

    layout.addWidget(group_box)

  def _on_metric_changed(self, _index: int):
    metric_id = self.metric_combo.currentData()
    if metric_id:
      self.logger.info(f"Metric changed: {metric_id}")
      self.metricChanged.emit(metric_id)

  def current_metric_id(self) -> str:
    return self.metric_combo.currentData() or DEFAULT_METRIC_ID
