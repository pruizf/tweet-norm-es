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

# logger
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
lgr, lfh = prep.set_log(__name__, logfile_name, False)

""" Basic Twitter Objects """

class Tweet:
    def __init__(self, tid, itext, logger=None):
        self.tid = tid
        self.itext = itext
        self.set_toks([])
        self.set_found_OOVs([])
        self.par_corr = []

    hasOOVs = None
    found_OOVs = None
    
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
                    # create OOV instance only if in reference annotations
                    if tok.form not in self.ref_OOVs:
                        lgr.warn("TID [{0}]: Skipping found OOV [{1}], posi [{2}], reason [Not in Ref]".format(
                            self.tid, repr(tok.form), idx))
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
        try:
            if ref_OOVs[self.tid] == []:
                self.hasOOVs = False
            else:
                self.hasOOVs = True
        except KeyError:
            self.hasOOVs = False

    def set_toks(self, toks):
        self.toks = toks
        
    def set_ref_OOVs(self, ref_OOVs):
        self.ref_OOVs = ref_OOVs

    def set_found_OOVs(self, found_OOVs):
        self.found_OOVs = found_OOVs

    def set_par_corr(self, tok_or_tweet, posi=None):
        """Set <tok_or_tweet> as a partially corrected version for the Tweet obj,
           or set <tok_or_tweet> as tok.form at par_cor's position <posi>"""
        if posi is not None:
            self.par_corr[posi].form = tok_or_tweet
        else:
            self.par_corr = tok_or_tweet
        par_out = []
        for idx, tok in enumerate(self.par_corr):
            if idx == posi:
                par_out.append("**{0}".format(repr(tok.form)))
            else:
                par_out.append(tok.form)
        lgr.debug("par_corr {0}".format(repr(par_out)))

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
        self.form = form
        # isOOV always True
        self.set_OOV_status(True)
        self.cands = {}
        self.entcands = {}
        self.has_cands = None
        self.has_LM_cands = None

    # Prepro
    safecorr = None
    abbrev = None
    runin = None
    ppro_recorr = None
    ppro_recorr_IV = None

    # Entities
    entcand = None

    # ED and LM
    cands_filtered = None
    #ed_filtered_ranked = None
    edbase = None
    edbase_lmsco = None
    best_ed_cando = None
    lmsco = None

    # Ranking
    keep_orig = None
    assess_edbase = None
    accept_best_ed_cando = None

    #ranking implicit from flags set here and ppro_recorr_IV
    befent = None
    aftent = None

    def add_cand(self, cand):
        self.cands[cand] = True

    def set_has_cands(self):
        if len(self.cands) > 0:
            self.has_cands = True
        else:
            self.has_cands = False
        return self.has_cands

    def set_has_LM_cands(self, boolean):
        if boolean:
            self.has_LM_cands = True
        else:
            self.has_LM_cands = False

    def set_safecorr(self, corr):
        self.safecorr = corr
    def set_ppro_recorr(self, corr):
        self.ppro_recorr = corr
    def set_ppro_recorr_IV(self, boolean):
        self.ppro_recorr_IV = boolean
    def set_abbrev(self, abbrev):
        self.abbrev = abbrev
    def set_runin(self, runin):
        self.runin = runin
    def set_correction(self, corr):
        self.correction = corr
    def set_edbase(self, form):
        self.edbase = form
    def set_edbase_lmsco(self, sco):
        self.edbase_lmsco = sco
    def set_lmsco(self, sco):
        self.lmsco = sco
        
