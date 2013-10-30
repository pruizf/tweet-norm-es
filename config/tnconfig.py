import inspect
import os
import sys

# ================================================================
EVAL = bool(1)              # test (1) vs. dev (0) sets
RESDIR = "/home/pruiz/DATA/projects/Tweet-Norm/results"
if not os.path.exists(RESDIR):
    os.makedirs(RESDIR)
# =================================================================

# PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
if not curdir in sys.path:
    sys.path.append(curdir)
# add data and processing dir to PYTHONPATH
parentdir = os.path.split(curdir)[0]
if not os.path.join(parentdir, "data") in sys.path:
    sys.path.append(os.path.join(parentdir, "data"))
if not os.path.join(parentdir, "twenor") in sys.path:
    sys.path.append(os.path.join(parentdir, "twenor"))

APPDIR = os.path.split(curdir)[0]
DATA = os.path.join(parentdir, "data")

# input files
if EVAL:
    ANNOTS = APPDIR + "/evaluation/eval/" + "tweet-norm-test600.txt"
    TEXTS = APPDIR + "/evaluation/eval/" + "test600_texts.txt"
    id_order = APPDIR + "/config/" + "sortorder_eval.txt"
else:
    ANNOTS = APPDIR + "/evaluation/dev/" + "newest-tweet-norm-dev500_annotated.txt"
    TEXTS = APPDIR + "/evaluation/dev/" + "dev500_texts.txt"
    id_order = APPDIR + "/config/" + "sortorder.txt"

# freeling 
USERTOK = os.path.join(DATA, "es-twit-tok.dat")
USERMAP = os.path.join(DATA, "es-twit-map.dat")


