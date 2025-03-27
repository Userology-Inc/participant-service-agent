import logging
import os
import sys

# Set up logger
logger = logging.getLogger("sarvam")
logger.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)

# Create console handler if not already set up
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
