import inspect
import os
import re
import sys

# BASIC ========================================================================
COMMENT = "Test easy way to pass final choice before entities to output dico"
RUNID = None
TAG = False                 # Tag with Freeling (1) or read tags from TAGSDIR (0)
ENV = "W"                   # Work, Home, Server
EVAL = bool(1)              # test (1) vs. dev (0) sets
if ENV == "W":
    RESDIR = "/home/pruiz/DATA/projects/Tweet-Norm/results2"
elif ENV == "H":
    RESDIR = "/home/ps/DATA/wk/VT/projects/Tweet-Norm/results2"
elif ENV == "S":
    RESDIR = "/home/VICOMTECH/share/Tweet-Norm2/results"
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
elif ENV == "S":
    ANACLI = "/usr/local/smtdev/freeling/bin/analyzer_client"
    ANA = "/usr/local/smtdev/freeling/bin/analyze"

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
# preprocessing: all files utf-8
doubledchar_dico = APPDIR + r"/data/" + "doubledchar-dic.txt"
IVDICO = APPDIR + r"/data/" + "aspell-es-expanded.dic"
SAFETOKENS = APPDIR + r"/data/" + "safelist.txt"
REGPREPRO = APPDIR + r"/data/" + "preprocessing.txt"
ABBREVS = APPDIR + r"/data/" + "abbreviations.txt"
RUNIN = APPDIR + r"/data/" + "runinwords.txt"
accept_all_IV_regex_outputs = False

# EDIT-DISTANCE ----------------------------------------------------------------
    #TODO: if costs ever get expressed with positive values,
    #      insert_accent_penalty would need to be positive to penalize
    #      (negative would promote)
acc_ins_penalty = -0.5 # for now negative values penalize. 
alphabet = ('bcdfghjklmnpqrstvwxyzaeiou', ['á', 'é', 'í', 'ó', 'ú', 'ü', 'ñ'])
maxdista = -1.5
distaw = 0.7 # weight for distance scores

# LANGUAGE MODELS --------------------------------------------------------------
increment_norm = True # ltr, use normalized tokens as context for later tokens
if ENV in ["W", "H"]:
    lmpath = APPDIR + "/data/" + "SUMATCasedLM_kenlm_es.arpa"
    #lmpath = "/home/VICOMTECH/share/Tweet-Norm/lms/es_strict_noht_lc.arpa"
if ENV == "S":
    lmpath = "/home/VICOMTECH/share/SUMAT/LanguageModels/OpenSubs/5-gram/es/OpenSubsLM.tc.5grams.es.arpa"

lm_window = 4
lmw = 0.3 # weight for lm scores

# EVALUATION -------------------------------------------------------------------
evalscript = APPDIR + "/scripts/" + "new-tweet-norm-eval.py"

# ENTITIES ---------------------------------------------------------------------
# entity dictionaries, all utf-8
entdir = APPDIR + r"/data/entities"
ent_use = {"jrc":      (1, "jrc_names.txt"),
           "geonames": (0, "geonames.txt"),       #tks 1 min to hash into a python dico
           "savas":    (1, "savas_es_names.txt"),
           "xtyle":    (1, "xtyle_names.txt")}
merge_iv_and_entities = False

# OTHER ------------------------------------------------------------------------
BLANKLINES_RE = re.compile(r"^\s*$")
COMMENTLINES_RE = re.compile(r"^#")
file_for_dumps = APPDIR + "/tests/" + "objdumps.txt"
