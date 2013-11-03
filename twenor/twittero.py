import codecs
import inspect
import logging
import os
import sys

# PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if not curdir in sys.path:
    sys.path.append(curdir)
parentdir = os.path.split(curdir)[0]
if not os.path.join(os.path.join(parentdir, "config")) in sys.path:
    sys.path.append(os.path.join(parentdir, "config"))

# app-specific imports
import tnconfig as tc
import preparation as prep


# this should all move to a function in preparation.py
# then import preparation here and mk logger with its fh and format
# create_logger(lgr_name, lfh_name)

##lgr = logging.getLogger(__name__)
##lfh = logging.FileHandler(os.path.join(tc.LOGDIR, "run_%s.log" % tc.RUNID))
##frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
##lfh.setFormatter(frmt)
##lgr.propagate = False #else writes to Python shell
##lgr.addHandler(lfh)
# logger
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % tc.RUNID)
lgr, lfh = prep.set_log(__name__, logfile_name)



""" Basic Twitter Objects """

class Tweet:
    def __init__(self, tid, itext, logger=None):
        self.tid = tid
        self.itext = itext
        self.set_toks([])
        self.set_found_OOVs([])

    hasOOVs = None
    
    def find_toks_and_OOVs(self):
        """Based on Freeling analyze ouptut, make Token and OOV instances for
           tweet's tokens, and set attributes lemma, posi, isOOV.
           OOV have only one column in Freeling's output."""
        fn = os.path.join(tc.TAGSDIR, "%s.tags" % self.tid)
        with codecs.open(fn, "r", "utf8") as fh:
            ana = fh.read()
            spana = [line for line in ana.split("\n") if not len(line) == 0]
            # (form, lemma, tag, index) tuples
            foletis = [(eline[1].split(" ")[0], eline[1].split(" ")[1],
                        eline[1].split(" ")[2], eline[0])
                       if len(eline[1].split(" ")) > 1
                       else (eline[1].split(" ")[0], "", "", eline[0])
                       for eline in enumerate(spana)]
            for foleti in foletis:
                ctok = Token(foleti[0])
                ctok.set_lemma(foleti[1])
                ctok.set_tag(foleti[2])
                ctok.set_posi(foleti[3])
                ctok.set_OOV_status(ctok.find_OOV_status())
                self.toks.append(ctok)
            for idx, tok in enumerate(self.toks):
                if tok.isOOV:
                    # skip what not in reference annotations
                    if tok.form not in self.ref_OOVs:
                        lgr.warn("Skipping found OOV [{}], posi [{}], TID [{}], reason [Not in Ref]".format(
                            repr(tok.form), idx, self.tid))
                        continue
                    self.toks[idx] = OOV(tok.form)
                    self.toks[idx].set_lemma(tok.lemma)
                    self.toks[idx].set_tag(tok.tag)
                    self.toks[idx].set_posi(tok.posi)

        self.set_found_OOVs([tok for tok in self.toks if isinstance(tok, OOV)])
        
    def cf_OOVs_found_vs_ref(self):
        """Compare found OOVs with reference ones. Log warning on differences."""
        found_OOV_forms = [oov.form for oov in self.found_OOVs]
        if len(found_OOV_forms) != len(self.ref_OOVs):
            lgr.warn("Len of Ref OOVs ({0}) ne len of found OOVs ({1}), TID {2}".format(
                len(self.ref_OOVs), len(found_OOV_forms), self.tid))
        if found_OOV_forms != self.ref_OOVs:
            lgr.warn("Ref OOVs ne found OOVs, TID {0}: REF {1} || FND {2}".format(
                self.tid, repr(self.ref_OOVs), repr(found_OOV_forms)))

    def find_OOV_status(self, ref_OOVs):
        if self.tid not in ref_OOVs:
            self.hasOOVs = False
        else:
            self.hasOOVs = True

    def set_toks(self, toks):
        self.toks = toks
        
    def set_ref_OOVs(self, ref_OOVs):
        self.ref_OOVs = ref_OOVs

    def set_found_OOVs(self, found_OOVs):
        self.found_OOVs = found_OOVs


class Token:
    def __init__(self, form):
        self.form = form

    isOOV = None
    lemma = None
    tag = None
    posi = None
    
    def find_OOV_status(self):
        if self.lemma == "":
            return True
        return False

    def set_lemma(self, lem):
        self.lemma = lem
    def set_tag(self, tag):
        self.tag = tag
    def set_posi(self, posi):
        self.posi = posi
    def set_OOV_status(self, Ostat):
        self.isOOV = Ostat

class OOV(Token):
    def __init__(self, form):
        Token.__init__(self, form)
        # isOOV always True
        self.set_OOV_status(True)
       
    def set_correction(corr):
        self.correction = corr
