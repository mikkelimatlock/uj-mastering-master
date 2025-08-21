"""
Logging configuration for the Audio Mastering Toolkit.
Provides CLI configurable logging with different verbosity levels.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", log_to_file: bool = False) -> logging.Logger:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level (ERROR, WARN, INFO, DEBUG, TRACE)
        log_to_file: Whether to also log to file
        
    Returns:
        Configured logger instance
    """
    # Convert level string to logging constant
    level_map = {
        'ERROR': logging.ERROR,
        'WARN': logging.WARNING,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'TRACE': 5  # Custom level below DEBUG
    }
    
    # Add custom TRACE level
    logging.addLevelName(5, 'TRACE')
    
    numeric_level = level_map.get(level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()  # Clear any existing handlers
    root_logger.addHandler(console_handler)
    
    # Optional file logging
    if log_to_file:
        file_handler = logging.FileHandler('audio_analysis.log')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    
    # Add trace method to all loggers
    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(5):
            self._log(5, message, args, **kwargs)
    
    logging.Logger.trace = trace
    
    # Create main application logger
    app_logger = logging.getLogger('audio_mastering')
    app_logger.info(f"Logging initialized at {level.upper()} level")
    
    return app_logger


def parse_log_args() -> tuple[str, bool]:
    """
    Parse command line arguments for logging configuration.
    
    Returns:
        Tuple of (log_level, log_to_file)
    """
    import argparse
    
    parser = argparse.ArgumentParser(add_help=False)  # Don't interfere with main arg parsing
    parser.add_argument('--log-level', '-l', 
                       choices=['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'],
                       default='INFO',
                       help='Set logging verbosity level')
    parser.add_argument('--log-file', action='store_true',
                       help='Also log to audio_analysis.log file')
    
    # Parse known args only (ignore others for main app)
    args, _ = parser.parse_known_args()
    
    return args.log_level, args.log_file