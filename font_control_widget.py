"""
Unified font control widget clustering all font-related manipulators.
Self-contained widget for easy layout management.
"""

import logging
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (QWidget, QComboBox, QVBoxLayout, QHBoxLayout, 
                            QLabel, QSlider, QPushButton, QGroupBox)
from PyQt5.QtCore import pyqtSignal, Qt

from font_manager import get_font_manager


class FontControlWidget(QWidget):
    """
    Unified font control widget containing all font-related manipulators.
    
    Provides clustered interface for:
    - Font selection (unified for Qt and matplotlib)
    - Qt font size adjustment
    - Plot regeneration controls
    """
    
    # Signals
    fontChanged = pyqtSignal(str, str)  # (font_name, font_type)
    fontSizeChanged = pyqtSignal(int)   # font_size
    plotRefreshRequested = pyqtSignal() # manual refresh request
    
    def __init__(self, parent=None):
        """Initialize the font control widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.font_manager = get_font_manager()
        self.available_fonts: Dict[str, str] = {}  # display_name -> actual_font_name
        
        # Font size bounds (reasonable range for GUI fonts)
        self.min_font_size = 8
        self.max_font_size = 12
        self.default_font_size = 10
        
        self.initUI()
        self.refresh_font_list()
        
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
        
        # Group box for visual clustering
        group_box = QGroupBox("Font Settings")
        group_layout = QVBoxLayout(group_box)
        
        # Font selector section
        font_section = self._create_font_selector_section()
        group_layout.addWidget(font_section)
        
        # Font size section
        size_section = self._create_font_size_section()
        group_layout.addWidget(size_section)
        
        # Control buttons section
        button_section = self._create_button_section()
        group_layout.addWidget(button_section)
        
        layout.addWidget(group_box)
        
    def _create_font_selector_section(self) -> QWidget:
        """Create the font selector section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Font label and dropdown
        font_label = QLabel("Font:")
        layout.addWidget(font_label)
        
        self.font_combo = QComboBox()
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        layout.addWidget(self.font_combo)
        
        return section
    
    def _create_font_size_section(self) -> QWidget:
        """Create the font size control section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Size label
        self.size_label = QLabel(f"Qt Font Size: {self.default_font_size}pt")
        layout.addWidget(self.size_label)
        
        # Size slider with value labels
        slider_layout = QHBoxLayout()
        
        # Min label
        min_label = QLabel(str(self.min_font_size))
        min_label.setFixedWidth(20)
        slider_layout.addWidget(min_label)
        
        # Slider
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(self.min_font_size)
        self.size_slider.setMaximum(self.max_font_size)
        self.size_slider.setValue(self.default_font_size)
        self.size_slider.setTickPosition(QSlider.TicksBelow)
        self.size_slider.setTickInterval(2)
        self.size_slider.valueChanged.connect(self.on_font_size_changed)
        slider_layout.addWidget(self.size_slider)
        
        # Max label
        max_label = QLabel(str(self.max_font_size))
        max_label.setFixedWidth(20)
        slider_layout.addWidget(max_label)
        
        layout.addLayout(slider_layout)
        
        return section
    
    def _create_button_section(self) -> QWidget:
        """Create the control buttons section."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Refresh plot button
        self.refresh_button = QPushButton("Refresh Plot")
        self.refresh_button.setToolTip("Regenerate current plot with new font settings")
        self.refresh_button.clicked.connect(self.on_refresh_plot_clicked)
        layout.addWidget(self.refresh_button)
        
        return section
    
    def refresh_font_list(self):
        """Refresh the list of available fonts."""
        self.logger.debug("Refreshing font list...")
        self.available_fonts.clear()
        
        try:
            # Get custom fonts from font manager
            custom_fonts = self.font_manager.loaded_fonts
            
            # Get system font candidates
            system_fonts = self.font_manager.get_available_system_fonts()[:10]
            
            # Clear combo box
            self.font_combo.clear()
            
            # Add custom fonts first (highest priority)
            if custom_fonts:
                for font_family, font_path in custom_fonts.items():
                    display_name = f"{font_family} (Custom)"
                    self.available_fonts[display_name] = font_family
                    self.font_combo.addItem(display_name)
                    self.logger.debug(f"Added custom font: {display_name}")
            
            # Add system fonts
            for font_name in system_fonts:
                display_name = f"{font_name} (System)"
                self.available_fonts[display_name] = font_name
                self.font_combo.addItem(display_name)
                self.logger.debug(f"Added system font: {display_name}")
            
            # Add default option with actual system font name
            system_font_name = self.font_manager.get_default_system_font_name()
            default_name = f"Default ({system_font_name})"
            self.available_fonts[default_name] = "default"
            self.font_combo.addItem(default_name)
            
            # Select startup font
            self._select_startup_font()
            
            self.logger.info(f"Font list refreshed: {len(self.available_fonts)} fonts available")
            
        except Exception as e:
            self.logger.error(f"Error refreshing font list: {e}")
            # Fallback: add default option only
            self.font_combo.clear()
            self.font_combo.addItem("Default (System)")
            self.available_fonts = {"Default (System)": "default"}
    
    def _select_startup_font(self):
        """Select the appropriate font on startup."""
        # Use font manager's startup font selection logic
        startup_font_name, startup_font_type = self.font_manager.select_startup_font()
        
        # Find the corresponding display name in our combo box
        target_display_name = None
        for display_name, actual_name in self.available_fonts.items():
            if actual_name == startup_font_name:
                target_display_name = display_name
                break
        
        # If we found the font, select it
        if target_display_name:
            index = self.font_combo.findText(target_display_name)
            if index >= 0:
                self.font_combo.setCurrentIndex(index)
                self.logger.info(f"Startup font selected: {target_display_name}")
                return
        
        # Fallback to default if we couldn't find the startup font
        for i in range(self.font_combo.count()):
            item_text = self.font_combo.itemText(i)
            if item_text.startswith("Default ("):
                self.font_combo.setCurrentIndex(i)
                self.logger.info(f"Startup font fallback: {item_text}")
                return
    
    def on_font_changed(self, display_name: str):
        """Handle font selection change."""
        if not display_name or display_name not in self.available_fonts:
            return
            
        actual_font_name = self.available_fonts[display_name]
        
        # Determine font type
        if "(Custom)" in display_name:
            font_type = "custom"
        elif "(System)" in display_name:
            font_type = "system"
        else:
            font_type = "default"
        
        self.logger.info(f"Font changed: {display_name} -> {actual_font_name} ({font_type})")
        
        # Apply the font change
        self._apply_font_change(actual_font_name, font_type)
        
        # Emit signal for external listeners (including auto-regeneration)
        self.fontChanged.emit(actual_font_name, font_type)
    
    def on_font_size_changed(self, size: int):
        """Handle font size change."""
        self.size_label.setText(f"Qt Font Size: {size}pt")
        self.logger.info(f"Qt font size changed: {size}pt")
        
        # Apply Qt font size change
        self._apply_font_size_change(size)
        
        # Emit signal for external listeners
        self.fontSizeChanged.emit(size)
    
    def on_refresh_plot_clicked(self):
        """Handle manual plot refresh button click."""
        self.logger.info("Manual plot refresh requested")
        self.plotRefreshRequested.emit()
    
    def _apply_font_change(self, font_name: str, font_type: str):
        """Apply the font change to both Qt and matplotlib."""
        try:
            # Use font manager's centralized font application
            success = self.font_manager.apply_font_selection(font_name, font_type)
            if not success:
                self.logger.warning(f"Font application may have failed: {font_name}")
                
        except Exception as e:
            self.logger.error(f"Error applying font change: {e}")
    
    def _apply_font_size_change(self, size: int):
        """Apply Qt font size change."""
        try:
            from PyQt5.QtCore import QCoreApplication
            from PyQt5.QtGui import QFont
            
            app = QCoreApplication.instance()
            if app:
                current_font = app.font()
                current_font.setPointSize(size)
                app.setFont(current_font)
                self.logger.debug(f"Qt font size set to: {size}pt")
                
        except Exception as e:
            self.logger.error(f"Error applying font size change: {e}")
    
    def get_current_font(self) -> tuple[str, str]:
        """
        Get currently selected font.
        
        Returns:
            tuple: (font_name, font_type)
        """
        display_name = self.font_combo.currentText()
        if display_name in self.available_fonts:
            actual_font_name = self.available_fonts[display_name]
            
            if "(Custom)" in display_name:
                font_type = "custom"
            elif "(System)" in display_name:
                font_type = "system"
            else:
                font_type = "default"
                
            return actual_font_name, font_type
        
        return "default", "default"
    
    def get_current_font_size(self) -> int:
        """
        Get current Qt font size.
        
        Returns:
            int: Current font size in points
        """
        return self.size_slider.value()
    
    def set_font(self, font_name: str):
        """
        Programmatically set the font selection.
        
        Args:
            font_name: Name of font to select
        """
        # Find matching display name
        for display_name, actual_name in self.available_fonts.items():
            if actual_name == font_name:
                index = self.font_combo.findText(display_name)
                if index >= 0:
                    self.font_combo.setCurrentIndex(index)
                    return
        
        self.logger.warning(f"Font not found in selector: {font_name}")
    
    def set_font_size(self, size: int):
        """
        Programmatically set the font size.
        
        Args:
            size: Font size in points (will be clamped to valid range)
        """
        clamped_size = max(self.min_font_size, min(self.max_font_size, size))
        self.size_slider.setValue(clamped_size)
        if clamped_size != size:
            self.logger.warning(f"Font size clamped: {size} -> {clamped_size}")