"""
Font management system with CJK fallback support.
Handles matplotlib and Qt font configuration with licensing-safe approach.
"""

import os
import logging
import platform
from pathlib import Path
from typing import List, Optional, Dict, Any

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QFontDatabase, QFont


class FontManager:
    """
    Centralized font management for CJK character support.
    
    Provides licensing-safe font fallback by:
    1. Loading fonts from local fonts/ directory (gitignored)
    2. Falling back to system CJK fonts
    3. Gracefully degrading to default fonts
    """
    
    def __init__(self, fonts_dir: str = "fonts"):
        """
        Initialize font manager.
        
        Args:
            fonts_dir: Directory name for custom fonts (relative to project root)
        """
        self.logger = logging.getLogger(__name__)
        self.fonts_dir = Path(__file__).parent / fonts_dir
        self.loaded_fonts: Dict[str, str] = {}
        self._matplotlib_configured = False
        self._qt_configured = False
        
        # CJK font preferences by platform and type
        self.system_font_fallbacks = {
            'Windows': {
                'serif': ['Yu Mincho', 'MS Mincho', '游明朝', 'ＭＳ 明朝'],
                'sans-serif': ['Yu Gothic UI', 'Meiryo', 'MS Gothic', '游ゴシック', 'メイリオ', 'ＭＳ ゴシック'],
                'monospace': ['MS Gothic', 'ＭＳ ゴシック']
            },
            'Darwin': {  # macOS
                'serif': ['Hiragino Mincho ProN', 'Yu Mincho', 'Times New Roman'],
                'sans-serif': ['Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Arial Unicode MS'],
                'monospace': ['Menlo', 'Monaco', 'Courier New']
            },
            'Linux': {
                'serif': ['Noto Serif CJK JP', 'Source Han Serif', 'DejaVu Serif'],
                'sans-serif': ['Noto Sans CJK JP', 'Source Han Sans', 'DejaVu Sans'],
                'monospace': ['Noto Sans Mono CJK JP', 'Source Code Pro', 'DejaVu Sans Mono']
            }
        }
    
    def initialize(self) -> bool:
        """
        Initialize font system for both matplotlib and Qt.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            self.logger.info("Initializing font management system...")
            
            # Load custom fonts if available
            custom_fonts_loaded = self._load_custom_fonts()
            
            # Configure matplotlib
            matplotlib_success = self._configure_matplotlib()
            
            # Configure Qt
            qt_success = self._configure_qt()
            
            success = matplotlib_success and qt_success
            
            if success:
                self.logger.info(f"Font system initialized successfully. Custom fonts: {custom_fonts_loaded}")
            else:
                self.logger.warning("Font system initialized with some issues")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Font system initialization failed: {e}")
            return False
    
    def _load_custom_fonts(self) -> int:
        """
        Load fonts from the fonts/ directory if it exists.
        
        Returns:
            int: Number of custom fonts loaded
        """
        if not self.fonts_dir.exists():
            self.logger.info(f"Custom fonts directory {self.fonts_dir} not found - using system fonts")
            return 0
        
        font_extensions = {'.ttf', '.otf', '.ttc'}
        fonts_loaded = 0
        
        try:
            for font_file in self.fonts_dir.iterdir():
                if font_file.suffix.lower() in font_extensions:
                    try:
                        # Load for matplotlib
                        fm.fontManager.addfont(str(font_file))
                        
                        # Load for Qt
                        font_id = QFontDatabase.addApplicationFont(str(font_file))
                        if font_id != -1:
                            font_families = QFontDatabase.applicationFontFamilies(font_id)
                            for family in font_families:
                                self.loaded_fonts[family] = str(font_file)
                            
                            fonts_loaded += 1
                            self.logger.debug(f"Loaded custom font: {font_file.name} -> {font_families}")
                        else:
                            self.logger.warning(f"Failed to load font for Qt: {font_file.name}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to load custom font {font_file.name}: {e}")
            
            if fonts_loaded > 0:
                # Clear matplotlib's font cache to recognize new fonts
                fm.fontManager._load_fontmanager(try_read_cache=False)
                
        except Exception as e:
            self.logger.error(f"Error loading custom fonts: {e}")
        
        return fonts_loaded
    
    def _configure_matplotlib(self) -> bool:
        """Configure matplotlib with appropriate CJK font fallbacks."""
        try:
            current_system = platform.system()
            fallback_fonts = self.system_font_fallbacks.get(current_system, 
                                                          self.system_font_fallbacks['Linux'])
            
            # Build font list: custom fonts + system fallbacks + matplotlib defaults
            font_list = []
            
            # Add custom fonts first (highest priority)
            font_list.extend(self.loaded_fonts.keys())
            
            # Add system CJK fonts
            font_list.extend(fallback_fonts['sans-serif'])
            
            # Add matplotlib defaults as final fallback
            font_list.extend(['DejaVu Sans', 'Arial', 'sans-serif'])
            
            # Update matplotlib configuration
            plt.rcParams['font.sans-serif'] = font_list
            plt.rcParams['font.family'] = 'sans-serif'
            
            # Ensure matplotlib can handle Unicode
            plt.rcParams['axes.unicode_minus'] = False
            
            self.logger.info(f"Matplotlib configured with font list: {font_list[:3]}...")
            self._matplotlib_configured = True
            return True
            
        except Exception as e:
            self.logger.error(f"Matplotlib font configuration failed: {e}")
            return False
    
    def _configure_qt(self) -> bool:
        """Configure Qt application with appropriate CJK fonts."""
        try:
            app = QCoreApplication.instance()
            if not app:
                self.logger.warning("No Qt application instance found - Qt font configuration skipped")
                return True
            
            # Get best available CJK font
            cjk_font = self._get_best_cjk_font()
            
            if cjk_font:
                # Set application-wide font
                font = QFont(cjk_font)
                app.setFont(font)
                self.logger.info(f"Qt configured with CJK font: {cjk_font}")
            else:
                self.logger.info("Qt using default system font (no specific CJK font found)")
            
            self._qt_configured = True
            return True
            
        except Exception as e:
            self.logger.error(f"Qt font configuration failed: {e}")
            return False
    
    def _get_best_cjk_font(self) -> Optional[str]:
        """
        Find the best available CJK font for the current system.
        
        Returns:
            str or None: Name of best available CJK font
        """
        # Check custom fonts first
        for font_name in self.loaded_fonts.keys():
            if self._is_cjk_capable(font_name):
                return font_name
        
        # Check system fonts
        current_system = platform.system()
        system_fonts = self.system_font_fallbacks.get(current_system, 
                                                     self.system_font_fallbacks['Linux'])
        
        available_fonts = set(fm.get_font_names())
        for font_name in system_fonts['sans-serif']:
            if font_name in available_fonts:
                return font_name
        
        return None
    
    def _is_cjk_capable(self, font_name: str) -> bool:
        """
        Check if a font supports CJK characters.
        Simple heuristic based on font name.
        """
        cjk_indicators = [
            'cjk', 'japanese', 'chinese', 'korean', 'han', 'noto', 'yu', 
            'hiragino', 'meiryo', 'gothic', 'mincho', '游', 'メイリオ', 
            'ゴシック', '明朝'
        ]
        font_lower = font_name.lower()
        return any(indicator in font_lower for indicator in cjk_indicators)
    
    def get_cjk_safe_title(self, title: str, fallback_encoding: str = 'utf-8') -> str:
        """
        Ensure title string is safe for display with current font configuration.
        
        Args:
            title: Original title string
            fallback_encoding: Encoding to use for problematic characters
            
        Returns:
            str: Safe title string for display
        """
        if not title:
            return title
        
        try:
            # Test if the string can be encoded/decoded properly
            title.encode(fallback_encoding).decode(fallback_encoding)
            return title
        except UnicodeError:
            # If there are encoding issues, create a safe fallback
            safe_title = title.encode(fallback_encoding, errors='replace').decode(fallback_encoding)
            self.logger.debug(f"Title encoding adjusted: {title[:50]}... -> {safe_title[:50]}...")
            return safe_title
    
    def create_fonts_directory_if_needed(self) -> Path:
        """
        Create the fonts directory and return its path.
        Useful for setup instructions.
        
        Returns:
            Path: Path to the fonts directory
        """
        self.fonts_dir.mkdir(exist_ok=True)
        return self.fonts_dir
    
    def get_font_installation_instructions(self) -> str:
        """
        Generate user instructions for installing CJK fonts.
        
        Returns:
            str: Multi-line instruction string
        """
        fonts_path = self.create_fonts_directory_if_needed()
        
        instructions = f"""CJK Font Installation Instructions:

1. Create or use the fonts directory: {fonts_path.absolute()}

2. Download CJK fonts (legally) from sources like:
   - Google Fonts (Noto Sans CJK, free & open source)
   - Adobe Source Han fonts (free & open source)  
   - System fonts from your OS (if redistribution is allowed)

3. Place .ttf, .otf, or .ttc font files in the fonts/ directory

4. Restart the application to load the new fonts

Note: The fonts/ directory is gitignored to avoid licensing issues.
System CJK fonts will be used as fallback if available.

Current system: {platform.system()}
Recommended fonts: {', '.join(self.system_font_fallbacks.get(platform.system(), {}).get('sans-serif', ['System default'])[:3])}
"""
        return instructions
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Generate a status report of the font system.
        
        Returns:
            dict: Status information
        """
        return {
            'matplotlib_configured': self._matplotlib_configured,
            'qt_configured': self._qt_configured,
            'custom_fonts_loaded': len(self.loaded_fonts),
            'custom_font_families': list(self.loaded_fonts.keys()),
            'fonts_directory_exists': self.fonts_dir.exists(),
            'fonts_directory_path': str(self.fonts_dir.absolute()),
            'current_matplotlib_fonts': plt.rcParams.get('font.sans-serif', [])[:5],
            'current_system': platform.system()
        }


# Global font manager instance
_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """
    Get the global font manager instance.
    Creates one if it doesn't exist.
    
    Returns:
        FontManager: Global font manager instance
    """
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager


def initialize_fonts() -> bool:
    """
    Initialize the global font system.
    Call this early in application startup.
    
    Returns:
        bool: True if successful
    """
    return get_font_manager().initialize()


def safe_title(title: str) -> str:
    """
    Convenience function to get CJK-safe title.
    
    Args:
        title: Original title
        
    Returns:
        str: Safe title for display
    """
    return get_font_manager().get_cjk_safe_title(title)