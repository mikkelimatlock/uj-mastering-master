#!/usr/bin/env python3
"""
Font setup utility for CJK character support.
Provides installation instructions and system font detection.
"""

import sys
import platform
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from font_manager import get_font_manager


def main():
    """Main font setup utility."""
    print("=== Audio Analysis Toolkit - CJK Font Setup ===\n")
    
    # Get font manager and show current status
    font_manager = get_font_manager()
    
    print("Current System Information:")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}\n")
    
    # Try to initialize fonts
    print("Initializing font system...")
    success = font_manager.initialize()
    
    # Show detailed status
    status = font_manager.get_status_report()
    print(f"Font system status: {'✓ OK' if success else '⚠ Issues detected'}")
    print(f"Matplotlib configured: {'✓' if status['matplotlib_configured'] else '✗'}")
    print(f"Qt configured: {'✓' if status['qt_configured'] else '✗'}")
    print(f"Custom fonts loaded: {status['custom_fonts_loaded']}")
    
    if status['custom_font_families']:
        print(f"Custom font families: {', '.join(status['custom_font_families'])}")
    
    print(f"Fonts directory: {status['fonts_directory_path']}")
    print(f"Directory exists: {'✓' if status['fonts_directory_exists'] else '✗'}")
    print()
    
    # Show current matplotlib font configuration
    print("Current matplotlib font stack:")
    for i, font in enumerate(status['current_matplotlib_fonts'][:8], 1):
        print(f"  {i}. {font}")
    print()
    
    # Show installation instructions
    print(font_manager.get_font_installation_instructions())
    
    # Test CJK character handling
    print("\n=== Testing CJK Character Handling ===")
    test_strings = [
        "English Title",
        "日本語のタイトル",  # Japanese
        "中文标题",  # Chinese
        "한국어 제목",  # Korean
        "Test - テスト",  # Mixed
    ]
    
    print("Testing font-safe title conversion:")
    for test_str in test_strings:
        safe_str = font_manager.get_cjk_safe_title(test_str)
        status_indicator = "✓" if test_str == safe_str else "⚠"
        print(f"  {status_indicator} '{test_str}' -> '{safe_str}'")
    
    print("\n=== Setup Complete ===")
    if success:
        print("Font system is ready for use!")
        if status['custom_fonts_loaded'] == 0:
            print("Consider adding CJK fonts to improve character display.")
    else:
        print("There were issues with font setup. Check the logs for details.")
        print("The application will still work but CJK characters may not display correctly.")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())