"""
Font selector widget providing GUI interface to font management system.
Self-contained widget that can be placed anywhere in the layout.
"""

import logging
from typing import List, Dict, Optional
from PyQt5.QtWidgets import QWidget, QComboBox, QVBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal

from font_manager import get_font_manager


class FontSelectorWidget(QWidget):
    """
    Self-contained font selector widget.
    
    Provides a dropdown interface to select fonts from available
    custom fonts and system fonts. Integrates with the FontManager
    backend for font discovery and application.
    """
    
    # Signal emitted when font selection changes
    fontChanged = pyqtSignal(str, str)  # (font_name, font_type)
    
    def __init__(self, parent=None):
        """Initialize the font selector widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.font_manager = get_font_manager()
        self.available_fonts: Dict[str, str] = {}  # display_name -> actual_font_name
        
        self.initUI()
        self.refresh_font_list()
        
    def initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Minimal margins for embedding
        
        # Label
        self.label = QLabel("Font:")
        layout.addWidget(self.label)
        
        # Font selector dropdown
        self.font_combo = QComboBox()
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        layout.addWidget(self.font_combo)
        
    def refresh_font_list(self):
        """Refresh the list of available fonts."""
        self.logger.debug("Refreshing font list...")
        self.available_fonts.clear()
        
        try:
            # Get custom fonts from font manager
            custom_fonts = self.font_manager.loaded_fonts
            
            # Get system font candidates
            system_fonts = self._get_system_font_candidates()
            
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
    
    def _get_system_font_candidates(self) -> List[str]:
        """
        Get list of available system fonts that are good candidates.
        
        Returns:
            List[str]: List of available system font names
        """
        # Use font manager's enhanced system font discovery
        return self.font_manager.get_available_system_fonts()[:10]  # Limit to reasonable number
    
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
        # Find any item that starts with "Default ("
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
        
        # Emit signal for any external listeners
        self.fontChanged.emit(actual_font_name, font_type)
    
    def _apply_font_change(self, font_name: str, font_type: str):
        """Apply the font change to the application."""
        try:
            # Use font manager's centralized font application
            success = self.font_manager.apply_font_selection(font_name, font_type)
            if not success:
                self.logger.warning(f"Font application may have failed: {font_name}")
                
        except Exception as e:
            self.logger.error(f"Error applying font change: {e}")
    
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