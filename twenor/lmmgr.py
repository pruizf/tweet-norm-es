import inspect
import os
import sys
import time

import srilm

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

#import kenlm
#if "klm" not in sys.modules["__main__"]:
#    klm = kenlm.LanguageModel(tc.lmpath)

class SLM:
    def __init__(self, arpa_path=tc.lmpath):
        self.arpa_path = arpa_path

    slmbin = None
    
    def create_bin_lm(self):
        """Create binary LM with SRILM from Arpa file"""
        if not "slmbin" in dir(sys.modules["__main__"]):
            msg = "= LM: Creating SRILM binary LM from Arpa file [{}], {}".format(
                self.arpa_path, time.asctime(time.localtime()))
            print msg ; lgr.debug(msg)
            slmbin = srilm.LM(self.arpa_path)
            msg = "Done, {}".format(time.asctime(time.localtime()))
            print msg ; lgr.debug(msg)
        return slmbin

    def find_left_context(self, idx, toks, window=tc.lm_window):
        """Find left-context from index <idx> in token list <toks>, for a
           window of <window> prior tokens"""
        if idx - window < 0:
            leftcon = ["<s>"]
            leftcon.extend(toks[0:idx])
        else:
            leftcon = toks[idx-window : idx]
        return leftcon

    def find_logprog_in_ctx(self, tok, context):
        """Srilm-logprob_strings score for tok and context"""
        context.reverse()
        return self.slmbin.logprob_strings(tok, context)

    def set_slmbin(self, lm):
        self.slmbin = lm
    
