# client to test LMMgr
import inspect
import os
import sys

# set PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if not curdir in sys.path:
    sys.path.append(curdir)
parentdir = os.path.split(curdir)[0]
if not os.path.join(os.path.join(parentdir, "config")) in sys.path:
    sys.path.append(os.path.join(parentdir, "config"))
if not os.path.join(os.path.join(parentdir, "data")) in sys.path:
    sys.path.append(os.path.join(parentdir, "data"))
if not os.path.join(os.path.join(parentdir, "scripts")) in sys.path:
    sys.path.append(os.path.join(parentdir, "scripts"))

import tnconfig as tc
import lmmgr


slmmgr = lmmgr.SLM()
if not "bslm" in dir():
    bslm = slmmgr.create_bin_lm()
slmmgr.set_slmbin(bslm)
tw = ["Esto", "es", "un", "caso", "mal", "excrito"]
posi = 3
lc = slmmgr.find_left_context(posi, tw)
print "LC", lc
lp = slmmgr.find_logprog_in_ctx(tw[posi], lc)

