# -*- coding: utf-8 -*-
import inspect
import os
import re
import sys

# PYTHONPATH
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

# app-specific imports
import tnconfig as tc
import preparation as prep

# logging
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
lgr, lfh = prep.set_log(__name__, logfile_name)

def recase(orig, prop, tweet):
    """Reproduce orginal's upper-case initial in the proposal"""
    global lgr
    to_recase = False
    toks = [tok.form for tok in tweet.toks]
    if orig not in toks:
        print "!! Posp ERROR: Original OOV not in original toks"
    sen_delims = [".", "!", "?", '"', "...", "(", ")", "/"]
    if orig[0].isupper():
        if orig == toks[0]:
            to_recase = True
        elif toks[toks.index(orig) -1] in sen_delims:
            to_recase = True
    if to_recase:
        postp = "".join([prop[0].upper(), prop[1:]])
        lgr.debug("PS Recased [{0}] into [{1}], Reason, Delim [{2}]".format(
            repr(prop), repr(postp), repr(toks[toks.index(orig)-1])))
        return postp
    else:
        return prop

# TODO: Allcaps tokens become caps-initial if caps initial variant in entity-dico
#       If lc variant in IV dico, see what ws convention is: lc, or original case?
#
#       Other: if jibberish string, put original and that's it


    
