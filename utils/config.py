import os
from dotenv import load_dotenv

load_dotenv()

AUTOPAS_DIR = os.getenv("AUTOPAS_DIR")
BUILD_DIR = os.getenv("BUILD_DIR")

# where to store the result run data and plots
DATA_DIR = os.getenv("DATA_DIR")
# where to get the experiment config files from
CONFIG_DIR = os.getenv("CONFIG_DIR")

# where the md-flexible executable is located
MD_FLEX_BINARY = os.getenv("MD_FLEX_BINARY")