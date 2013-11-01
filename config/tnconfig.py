import inspect
import os
import sys

# ==============================================================================
ENV = "H"                   # Work, Home, Server
EVAL = bool(1)              # test (1) vs. dev (0) sets
if ENV == "W":
    RESDIR = "/home/pruiz/DATA/projects/Tweet-Norm/results2"
elif ENV == "H":
    RESDIR = "/home/ps/DATA/wk/VT/projects/Tweet-Norm/results2"
if not os.path.exists(RESDIR):
    os.makedirs(RESDIR)
TAG = False                 # Tag with Freeling (1) or read tags from TAGSDIR (0)
RUNID = 1
# ==============================================================================

# PATHS ------------------------------------------------------------------------
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

# I/O --------------------------------------------------------------------------
if EVAL:
    ANNOTS = APPDIR + "/evaluation/eval/" + "tweets-test-reference.txt"
    TEXTS = APPDIR + "/evaluation/eval/" + "test600_texts.txt"
    id_order = APPDIR + "/config/" + "sortorder_eval.txt"
else:
    ANNOTS = APPDIR + "/evaluation/dev/" + "newest-tweet-norm-dev500_annotated.txt"
    TEXTS = APPDIR + "/evaluation/dev/" + "dev500_texts.txt"
    id_order = APPDIR + "/config/" + "sortorder.txt"

TAGSDIR = os.path.join(os.path.split(os.path.split(curdir)[0])[0], "tagged")

if EVAL:
    OUTFN = os.path.join(RESDIR, "testset_run_%s.txt" % RUNID)
else:
    OUTFN = os.path.join(RESDIR, "devset_run_%s.txt" % RUNID)

EVALFN = OUTFN.replace(".txt", "_eval.txt")

# FREELING ---------------------------------------------------------------------
if ENV == "W":
    ANACLI = "/usr/local/bin/analyzer_client" 
    ANA = "/usr/local/bin/analyze"
elif ENV == "H":
    ANACLI = "/home/ps/tools/freeling-3.0/freeling/bin/analyzer_client"
    ANA = "/home/ps/tools/freeling-3.0/freeling/bin/analyze"

USERTOK = os.path.join(DATA, "es-twit-tok.dat")
USERMAP = os.path.join(DATA, "es-twit-map.dat")

# server to tag with options used for devset
fl_port = 8064
fl_server = ["--server on",
             "-p %s" % fl_port]

# opts for tagging like in devset
fl_options = ["-f es.cfg",
              "--flush",
              "--ftok %s" % USERTOK,
              "--usr",
              "--fmap %s" % USERMAP,
              "--outf morfo",
              "--noprob",
              "--noloc",
              #options added bc of misalignments w devset
              "--noner",
              "--nortkcon",
              "--nortk"]

# EVALUATION -------------------------------------------------------------------
evalscript = APPDIR + "/scripts/" + "new-tweet-norm-eval.py"
