import os

# this file is automatically updated when distutils are running the setup
__version__ = "98.7"
# variable used to enable some device-specific features
DEVICE_CUSTOMIZATION = "turris"  # should be either "turris" or "omnia"

BASE_DIR = os.path.dirname(__file__)
