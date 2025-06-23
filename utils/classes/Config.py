import os
import importlib.util

if importlib.util.find_spec("dotenv") is not None:
    from dotenv import load_dotenv
    load_dotenv()

    AUTOPAS_DIR = os.getenv("AUTOPAS_DIR")
    BUILD_DIR = os.getenv("BUILD_DIR")

    # where to store the resulting run data
    DATA_DIR = os.getenv("DATA_DIR")
    # where to get the experiment config files from
    CONFIG_DIR = os.getenv("CONFIG_DIR")
    # where the md-flexible executable is located
    MD_FLEX_BINARY = os.getenv("MD_FLEX_BINARY")
    PLOT_DATA= os.getenv("PLOT_DATA")
    IS_HPC=True
    
else:
    # CM-4 does not offer dotenv
    AUTOPAS_DIR = "/dss/dsshome1/09/ge92hed2/AutoPas/"
    BUILD_DIR = "/dss/dsshome1/09/ge92hed2/AutoPas/build/"
    DATA_DIR = "/dss/dsshome1/09/ge92hed2/data/unplotted-data/"
    CONFIG_DIR = "/dss/dsshome1/09/ge92hed2/bachelor-thesis/experiments/"
    MD_FLEX_BINARY="/dss/dsshome1/09/ge92hed2/AutoPas/build/examples/md-flexible/md-flexible"
    PLOT_DATA=""
    IS_HPC=True

