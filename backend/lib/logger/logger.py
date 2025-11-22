"""
Simple python logger
"""

import logging
from lib.config.settings import get_settings

settings = get_settings()

log_level = logging.DEBUG if settings.env == "development" else logging.INFO

# Configure basic logging (e.g., to console)
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s: %(message)s")

# Get an instance of our custom logger
log = logging.getLogger()
