# CJK Font Support Implementation

This document describes the CJK (Chinese, Japanese, Korean) font fallback system implemented for the Audio Analysis Toolkit.

## Problem Statement

The application displays song titles and metadata that may contain CJK characters from Japanese, Chinese, or Korean music files. The default matplotlib font (DejaVu Sans) lacks CJK glyphs, causing:
- Matplotlib warnings about missing glyphs
- Incorrect character rendering (squares, question marks, etc.)
- Poor user experience for CJK music collections

## Solution Architecture

### 1. Font Manager System (`font_manager.py`)

A centralized font management system that handles both matplotlib and Qt font configuration:

**Key Features:**
- **Licensing-safe**: Uses local `fonts/` directory (gitignored) for custom fonts
- **Graceful fallback**: System CJK fonts → matplotlib defaults
- **Cross-platform**: Windows, macOS, Linux font detection
- **Modular design**: Single responsibility for font configuration

**Font Priority Order:**
1. Custom fonts from `fonts/` directory (highest priority)
2. System CJK fonts (platform-specific)
3. Default fonts (fallback)

### 2. Safe Title Processing

All text that might contain CJK characters is processed through `safe_title()` function:
- Ensures proper encoding handling
- Provides fallback for problematic characters
- Maintains original text when possible

### 3. Integration Points

The font system is integrated at these key locations:

#### Application Startup (`main.py`)
```python
# Initialize font system before creating any widgets
font_success = initialize_fonts()
```

#### Plot Titles (`plotting_engine.py`, `master_core.py`)
```python
ax.set_title(safe_title(os.path.basename(file_path)))
```

#### Metadata Display
```python
song_name = safe_title(f"{audio['artist'][0]} - {audio['title'][0]}")
```

## Usage Instructions

### Quick Setup

1. **Run the setup utility:**
```bash
python setup_fonts.py
```

2. **For enhanced CJK support, add fonts to the `fonts/` directory:**
   - Download free CJK fonts (Noto Sans CJK, Source Han Sans, etc.)
   - Place .ttf/.otf/.ttc files in `fonts/` directory
   - Restart the application

### Font Directory Structure
```
uj-mastering-master/
├── fonts/                    # Gitignored
│   ├── NotoSansCJK-Regular.ttc
│   ├── SourceHanSans-Regular.otf
│   └── [other CJK fonts]
└── [application files]
```

### Supported Font Formats
- `.ttf` (TrueType Font)
- `.otf` (OpenType Font) 
- `.ttc` (TrueType Collection)

## Platform-Specific Behavior

### Windows
**System Fonts Used:**
- Yu Gothic UI, Meiryo, MS Gothic (sans-serif)
- Yu Mincho, MS Mincho (serif)

### macOS
**System Fonts Used:**
- Hiragino Sans, Yu Gothic (sans-serif)
- Hiragino Mincho ProN, Yu Mincho (serif)

### Linux
**System Fonts Used:**
- Noto Sans CJK JP, Source Han Sans (sans-serif)
- Noto Serif CJK JP, Source Han Serif (serif)

## Technical Implementation Details

### Font Detection Algorithm

1. **Custom Font Loading:**
   ```python
   # Load for matplotlib
   fm.fontManager.addfont(str(font_file))
   
   # Load for Qt
   font_id = QFontDatabase.addApplicationFont(str(font_file))
   ```

2. **System Font Fallback:**
   ```python
   available_fonts = set(fm.get_font_names())
   for font_name in system_fonts['sans-serif']:
       if font_name in available_fonts:
           return font_name
   ```

3. **Matplotlib Configuration:**
   ```python
   plt.rcParams['font.sans-serif'] = font_list
   plt.rcParams['font.family'] = 'sans-serif'
   plt.rcParams['axes.unicode_minus'] = False
   ```

### Error Handling

The system is designed to be fault-tolerant:
- Missing fonts directory → Use system fonts
- Font loading failures → Log warnings, continue
- Encoding errors → Apply safe character replacement
- No CJK fonts found → Graceful degradation to defaults

## Licensing Considerations

### Safe Practices
- **Custom fonts directory is gitignored** to avoid committing proprietary fonts
- **System fonts are detected, not redistributed**
- **Open source font recommendations** (Noto, Source Han families)
- **No font files included in repository**

### Recommended Free CJK Fonts
1. **Google Noto Fonts** (SIL Open Font License)
   - Noto Sans CJK JP/SC/TC/KR
   - Comprehensive CJK coverage

2. **Adobe Source Han Fonts** (SIL Open Font License)
   - Source Han Sans
   - Source Han Serif

## Testing and Debugging

### Font Status Report
```python
from font_manager import get_font_manager
status = get_font_manager().get_status_report()
print(status)
```

### Test CJK Characters
```bash
python setup_fonts.py
```

### Logging
Font system operations are logged at appropriate levels:
- INFO: Successful initialization
- DEBUG: Font loading details  
- WARNING: Missing fonts, fallbacks used
- ERROR: Critical font system failures

## Future Improvements

### Potential Enhancements
1. **Dynamic Font Switching:** Per-language font selection
2. **Font Caching:** Faster startup with font cache
3. **User Preferences:** GUI for font selection
4. **Font Metrics:** Analyze font quality for CJK rendering

### Performance Considerations
- Font loading is done once at startup
- Font cache clearing only when necessary
- Minimal performance impact on audio processing

## Troubleshooting

### Common Issues

**Issue:** CJK characters still show as squares
- **Solution:** Install CJK fonts in `fonts/` directory or check system font availability

**Issue:** Font warnings in console
- **Solution:** Run `python setup_fonts.py` to check font configuration

**Issue:** Application startup slower after font system
- **Solution:** This is normal on first run; subsequent starts should be faster

### Debug Commands
```bash
# Check font system status
python setup_fonts.py

# Test with specific log level
python main.py --log-level DEBUG

# Test matplotlib font configuration
python -c "import matplotlib.pyplot as plt; print(plt.rcParams['font.sans-serif'])"
```

## Conclusion

This CJK font support implementation provides:
- **Robust fallback system** ensuring CJK characters display properly
- **Licensing compliance** by avoiding font redistribution
- **Cross-platform compatibility** with platform-specific font preferences  
- **Clean architecture** with separation of font management concerns
- **User-friendly setup** with clear instructions and status reporting

The system gracefully handles missing fonts and provides clear guidance for optimal CJK character rendering while maintaining the existing application functionality.