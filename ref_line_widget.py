"""
Reference-line management: a side-panel list of custom horizontal markers plus a
properties dialog.

`RefLineControlWidget` is a pure view over a list of `RefLineProps` owned by the
main window: it renders the list and emits intents (add / edit / remove / clear).
`RefLineDialog` edits one line's value, colour, line style, and tag.
"""

import logging

from PyQt5.QtWidgets import (
  QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QPushButton,
  QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QLineEdit, QColorDialog,
  QDialogButtonBox,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal

from plotspec import RefLineProps


_STYLE_CHOICES = [("Solid", "solid"), ("Dashed", "dash"), ("Dotted", "dot")]


class RefLineDialog(QDialog):
  """Edit one reference line's properties. Read the result via `result_props`."""

  def __init__(self, parent, props: RefLineProps):
    super().__init__(parent)
    self.setWindowTitle("Reference line")
    self._color = props.color

    form = QFormLayout(self)

    self.value_spin = QDoubleSpinBox()
    self.value_spin.setRange(-1e6, 1e6)
    self.value_spin.setDecimals(2)
    self.value_spin.setValue(props.value)
    form.addRow("Value:", self.value_spin)

    self.color_button = QPushButton()
    self.color_button.clicked.connect(self._pick_color)
    self._refresh_color_button()
    form.addRow("Colour:", self.color_button)

    self.style_combo = QComboBox()
    for label, key in _STYLE_CHOICES:
      self.style_combo.addItem(label, key)
    idx = self.style_combo.findData(props.style)
    if idx >= 0:
      self.style_combo.setCurrentIndex(idx)
    form.addRow("Line style:", self.style_combo)

    self.label_edit = QLineEdit(props.label)
    self.label_edit.setPlaceholderText("(optional tag)")
    form.addRow("Tag:", self.label_edit)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(self.accept)
    buttons.rejected.connect(self.reject)
    form.addRow(buttons)

  def _pick_color(self):
    chosen = QColorDialog.getColor(QColor(self._color), self, "Reference line colour")
    if chosen.isValid():
      self._color = chosen.name()
      self._refresh_color_button()

  def _refresh_color_button(self):
    self.color_button.setText(self._color)
    # Show the colour as the button's background for a quick read.
    self.color_button.setStyleSheet(f"background-color: {self._color};")

  def result_props(self) -> RefLineProps:
    return RefLineProps(
      value=float(self.value_spin.value()),
      color=self._color,
      style=self.style_combo.currentData(),
      label=self.label_edit.text().strip(),
    )


class RefLineControlWidget(QWidget):
  """List of reference lines with Add / Edit / Remove / Clear controls."""

  addRequested = pyqtSignal()
  editRequested = pyqtSignal(int)
  removeRequested = pyqtSignal(int)
  clearRequested = pyqtSignal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self.logger = logging.getLogger(__name__)
    self.initUI()

  def initUI(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(5, 5, 5, 5)

    group_box = QGroupBox("Reference lines")
    group_layout = QVBoxLayout(group_box)

    self.line_list = QListWidget()
    self.line_list.setMaximumHeight(110)
    self.line_list.itemDoubleClicked.connect(self._on_double_click)
    group_layout.addWidget(self.line_list)

    row = QHBoxLayout()
    self.add_button = QPushButton("Add")
    self.add_button.clicked.connect(self.addRequested.emit)
    row.addWidget(self.add_button)

    self.edit_button = QPushButton("Edit…")
    self.edit_button.clicked.connect(self._emit_edit)
    row.addWidget(self.edit_button)

    self.remove_button = QPushButton("Remove")
    self.remove_button.clicked.connect(self._emit_remove)
    row.addWidget(self.remove_button)

    self.clear_button = QPushButton("Clear")
    self.clear_button.clicked.connect(self.clearRequested.emit)
    row.addWidget(self.clear_button)

    group_layout.addLayout(row)
    layout.addWidget(group_box)

  def set_lines(self, lines: list[RefLineProps]):
    """Repopulate the list display from the current props (preserving selection)."""
    current = self.line_list.currentRow()
    self.line_list.clear()
    for p in lines:
      tag = f"  {p.label}" if p.label else ""
      self.line_list.addItem(f"{p.value:.2f}{tag}")
    if 0 <= current < self.line_list.count():
      self.line_list.setCurrentRow(current)

  def _selected_row(self) -> int:
    return self.line_list.currentRow()

  def _emit_edit(self):
    row = self._selected_row()
    if row >= 0:
      self.editRequested.emit(row)

  def _emit_remove(self):
    row = self._selected_row()
    if row >= 0:
      self.removeRequested.emit(row)

  def _on_double_click(self, _item):
    self._emit_edit()
