#!/usr/bin/env python3
"""
Demo script showing the different logging levels available.
Usage examples:

python demo_logging.py --log-level=ERROR
python demo_logging.py --log-level=INFO
python demo_logging.py --log-level=DEBUG
python demo_logging.py --log-level=TRACE --log-file
"""

import sys
from logger_setup import setup_logging, parse_log_args

def main():
    # Parse logging configuration
    log_level, log_to_file = parse_log_args()
    
    # Initialize logging
    logger = setup_logging(log_level, log_to_file)
    
    # Demo different log levels
    print(f"\n=== Audio Mastering Toolkit Logging Demo ===")
    print(f"Log Level: {log_level}")
    print(f"Log to File: {log_to_file}")
    print(f"============================================\n")
    
    # Test all logging levels
    logger.error("This is an ERROR message - critical failures only")
    logger.warning("This is a WARNING message - non-fatal issues")
    logger.info("This is an INFO message - key operations")
    logger.debug("This is a DEBUG message - detailed processing steps")
    logger.trace("This is a TRACE message - granular details")
    
    print(f"\nDemo complete! Messages above {log_level} level are visible.")
    if log_to_file:
        print("Check 'audio_analysis.log' for file output.")

if __name__ == '__main__':
    main()