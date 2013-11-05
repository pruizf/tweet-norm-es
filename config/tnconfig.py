import inspect
import os
import re
import sys

# BASIC ========================================================================
COMMENT = "test safetokens"
RUNID = None
TAG = False                 # Tag with Freeling (1) or read tags from TAGSDIR (0)
ENV = "W"                   # Work, Home, Server
EVAL = bool(1)              # test (1) vs. dev (0) sets
if ENV == "W":
    RESDIR = "/home/pruiz/DATA/projects/Tweet-Norm/results2"
elif ENV == "H":
    RESDIR = "/home/ps/DATA/wk/VT/projects/Tweet-Norm/results2"
if not os.path.exists(RESDIR):
    os.makedirs(RESDIR)
BASELINE = False
# ==============================================================================

# LOGGING ----------------------------------------------------------------------
loglevel = "DEBUG"

# PATHS ------------------------------------------------------------------------
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
if not curdir in sys.path:
    sys.path.append(curdir)
# add data and processing dir to PYTHONPATH
APPDIR = os.path.split(curdir)[0]
if not os.path.join(APPDIR, "data") in sys.path:
    sys.path.append(os.path.join(APPDIR, "data"))
if not os.path.join(APPDIR, "twenor") in sys.path:
    sys.path.append(os.path.join(APPDIR, "twenor"))

DATA = os.path.join(APPDIR, "data")
LOGDIR = os.path.join(APPDIR, "logs")
if not os.path.exists(LOGDIR):
    os.makedirs(LOGDIR)


# I/O --------------------------------------------------------------------------
RUNID_FILE = APPDIR + "/config/" + "runid"

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
    # run id completed in calling modules
    OUTFN = os.path.join(RESDIR, "testset_run_{0}.txt")
else:
    OUTFN = os.path.join(RESDIR, "devset_run_{0}.txt")

EVALFN = OUTFN.replace(".txt", "_eval.txt")
CUMULOG = os.path.join(APPDIR, "cumulog.txt")

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
fl_server = ["--server on", "-p %s" % fl_port]

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

# DATA -------------------------------------------------------------------------
SAFETOKENS = APPDIR + r"/data/" + "safelist.txt"


# EVALUATION -------------------------------------------------------------------
evalscript = APPDIR + "/scripts/" + "new-tweet-norm-eval.py"

# OTHER ------------------------------------------------------------------------
BLANKLINES_RE = re.compile(r"^\s*$")
COMMENTLINES_RE = re.compile(r"^#")
file_for_dumps = APPDIR + "/tests/" + "objdumps.txt"
