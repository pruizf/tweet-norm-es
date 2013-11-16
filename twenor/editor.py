# -*- coding: utf-8 -*-
import codecs
from collections import defaultdict
import os
import re

import tnconfig as tc
import preparation as prep

# logging
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
lgr, lfh = prep.set_log(__name__, logfile_name, False)

class EdScoreMatrix:
    """Methods to read cost matrix from module in arg cost_module
       and to find costs for individual character-edits."""

    def __init__(self, cost_module):
        self.costm = cost_module

    row_names = None
    col_names = None    
    matrix_conts = None
    accented_chars = [u'\xe1', u'\xe9', u'\xed', u'\xf1', u'\xf3', u'\xfa', u'\xfc']
    matrix_stats = {"max" : None, "min" : None, "ave" : None}

    def read_cost_matrix(self):
        """Read cost matrix into a hash. Set instance values for them"""
        row_names = self.costm.row_names.strip().split("\t")
        col_names = self.costm.col_names.strip().split("\t")
        costs = self.costm.costs

        # matrix_cont is list of lists
        #   cost_lines[x] is row nbr, cost_lines[y] is col nbr
        matrix_conts = [line.split("\t") for line in costs.split("\n")]

        # check row and col lengths
        lens = set([len(line) for line in matrix_conts])
        if len(list(lens)) > 1:
            print "!! Cost lines have unequal length"
            sys.exit(2)

        if list(lens)[0] != len(col_names):
            print "!! Amount of column names does not match amount of columns"
            sys.exit(2)

        if list(lens)[0] != len(matrix_conts):
            print "!! Amount of row names does not match amount of rows"

        # set values
        self.row_names = row_names
        self.col_names = col_names
        self.matrix_conts = matrix_conts

    def find_matrix_stats(self):
        """Calculate and set max, min, ave for cost-matrix values"""
        all_costs = []
        for line in self.matrix_conts:
            for cost in line:
                all_costs.append(float(cost))
        min_cost = min(all_costs)
        # TODO: may need to change cost < 0 if make costs positive
        max_cost = max([cost for cost in all_costs if cost < 0])
        ave_cost = float(sum(all_costs)) / len(all_costs)
        # set vals
        self.matrix_stats["min"] = min_cost
        self.matrix_stats["max"] = max_cost
        self.matrix_stats["ave"] = ave_cost

    def create_matrix_hash(self):
        """Hash cost-matrix contents. ic stands for incorrect character, cc stands for
           correct character"""
        skip_chars = ["SP"]
        names_map = {"YCorrNULL" : "zero", "XErrNULL" : "zero"}
        cost_dico = {}
        colno = 0
        for cc in self.col_names:
            ccd = cc.decode("utf8")
            rowno = 0
            if cc in skip_chars:
                colno += 1
                continue
            if cc in names_map:
                cc = names_map[cc]
            cost_dico[ccd] = {}
            for ic in self.row_names:
                if ic in skip_chars:
                    rowno += 1
                    continue
                if ic in names_map:
                    ic = names_map[ic]
                icd = ic.decode("utf8")
                if float(self.matrix_conts[rowno][colno]) == 0 and cc != ic:
                    # TODO: what's this case for?
                    cost_dico[ccd][icd] = self.matrix_stats["ave"]
                else:
                    cost_dico[ccd][icd] = float(self.matrix_conts[rowno][colno])
                # extra-penalize corrections that delete an accent
                #     i.e. that consider the accented character to be incorrect
                if icd in self.accented_chars:
                    cost_dico[ccd][icd] += tc.acc_ins_penalty
                rowno += 1
            colno += 1
        return cost_dico
    

class Candidate:
    def __init__(self, form):
        self.form = form

    dista = None
    apptimes = None
    candtype = None # "re", "lev" (regex or lev-distance based)
    lmsco = None
    lmctx = None # context for LM score
    inLM = None

    def set_dista(self, dista):
        self.dista = dista
    def set_candtype(self, typ):
        self.candtype = typ
    def set_lmsco(self, sco):
        self.lmsco = sco
    def set_lmctx(self, ctx):
        self.lmctx = ctx
    def set_inLM(self, boolean):
        self.inLM = boolean


class EdManager:
    """Computes correction-candidates for a term, and edit-distances between
       the term and the candidate. Requires info about correction weights (arg cws)
       and an IV dictionary (ivdico)"""

    def __init__(self, editcosts, ivdico):
        self.editcosts = editcosts
        self.ivdico = ivdico

    alphabet = None

    def prep_alphabet(self, alphabet=tc.alphabet):
        """ """ 
        alphabet_all = list(alphabet[0])
        # In config, entered the alphabet as strings. Decode using utf-8,
        # in order to be able to join to other unicode in edits1
        alphabet_all.extend([a.decode("utf-8") for a in alphabet[1]])
        self.alphabet = alphabet_all

    def rgdist(self, oov):
        """Regex-based distance. If OOV matches certain contexts, some candidates
           need special weights. E.g. "ao$ => ado" should cost little. Calculate
           these special weights. 
           Return tuple with
               [1] hash, keys: candidates, values: distances
               [2] hash, keys: candidates, values: times cand has been matched by a regex
        """
        # Ordered regexes. Format: (incorrect, correct)
        # TODO: treat side effects like laa=>lada, mia=>mía, solaa=>solada
        #       any stats (even unigram freq) may get rid of it wout extra lists
        # TODO: more precise regexes cos some (those w "h") are unlikely to bring good
        #       candidates
        subs_tups = [('gi', 'gui'), ('ge', 'gue'),
                     ('q(?!ui)', 'que'),
                     ('qe', 'que'), ('qi', 'qui'), ('ke', 'que'), ('ki', 'qui'),
                     ('nio', u'ño'), ('nia', u'ña'), ('nyo', u'ño'), ('nya', u'ña'),
                     ('x','ch'), ('y', 'll'), ('ll', 'y'),
                     ('ao$','ado'),('io$','ido'),('aa$','ada'),('ia$','ida'),
                     ('(?<!h)a','ha'), ('(?<!h)e','he'), ('(?<!h)i','hi'),
                     ('(?<!h)o','ho'),('(?<!h)u','hu'),
                     ('h$','s'),
                     ('g', 'ge'), ('d', 'de'), ('p', 'pe'), ('t','te'),
                     ('b','be'), ('q(?!u)','qu'), ('k','ca'), ('k', 'qu'), 
                     ('oy', 'oi'), ('ay', 'ai')]
        subs = dict(subs_tups)

        subs_keys = [tup[0] for tup in subs_tups]
        apptimes = {}
        result = {}
        cand = oov        
        for reg in sorted(subs, key=lambda x: subs_keys.index(x)):
            cand_bef = cand
            patt = re.compile(reg, re.IGNORECASE)
            # recursive            
            cand = re.sub(patt, subs[reg], cand)
            if not cand == cand_bef:
                apptimes.setdefault(cand, 0)
                # record how many times a rule has applied for cand
                apptimes[cand] += 1
                try:
                    apptimes[cand] += apptimes[cand_bef]
                except KeyError:
                    pass
                result.setdefault(cand, 0)
                result[cand] = -0.5 * apptimes[cand]
        for cand in result.keys():
            if cand not in self.ivdico:
                del result[cand]
            elif cand == oov:
                del result[cand]
        lgr.debug("RED RES {0}, APPT {1}".format(repr(result), repr(apptimes)))
        return {"cands": result, "apptimes" : apptimes}
    
    def edits1(self, word):
        """Generate candidates at Lev distance 1. From Norvig speller."""
        splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes    = [a + b[1:] for a, b in splits if b]
        replaces   = [a + c + b[1:] for a, b in splits for c in self.alphabet if b]
        inserts    = [a + c + b     for a, b in splits for c in self.alphabet]
        edits1 = set(deletes + replaces + inserts)
        #lgr.debug("++ All generated Edits1: %s" % repr(generated_edits1)) #large
        return edits1

    def generate_candidates(self, word):
        """Generate candidates at Lev distance 2 based on distance 1 edits,
           and return only those in known-words dictionary. Based on Norvig."""
        known2 = set([e2 for e1 in self.edits1(word) for e2 in self.edits1(e1)
                  if e2 in self.ivdico])
        cands = self.known(self.edits1(word)).union(known2)
        cands = [cand.decode("utf8") if type(cand) is str else cand for cand in cands]
        lgr.debug("DisED Candset %s: %s" % (repr(word), repr(sorted(list(cands)))))
        return cands

    def known(self, words):
        """Filter a list of words, returning only those in known-words dico.
           From Norvig."""
        return set(w for w in words if w in self.ivdico)

    def find_cost(self, a,b):
        """<b> OOV, <a> Cand. Return single-character-edit cost for changing
           'b' (from oov under study) into 'a' (from edit-candidate under study)
           The cost-matrix is organized as mat[corr][incorr]
           Assumes that "a" and "b" are utf8-decoded"""
        if type(a) is not unicode and a != "zero":
            lgr.warn("Not unicode: [{0}]".format(repr(a)))

        elif type(b) is not unicode and b != "zero":
            lgr.warn("Not unicode: [{0}]".format(repr(b)))
            
        if a == b:
            cost = 0
        else:
            try:
                cost = self.editcosts[a.lower()][b.lower()]
            except KeyError, msg:
                #if a != "zero" and b != "zero":
                #    print "KeyError, a: %s, b: %s || Bad Key: %s" % (a, b, msg) #debug
                cost = -1
        #TODO: case-sensitivity how?
        #if a.lower() == b or b.lower() and not a== b:
        #    cost += -0.5

        #print "looking for costs between", repr(a), repr(b) #debug
        return 0 - cost # matrix has neg numbers, min() below won't work if not do "0 -" here

    def levdist(self, s1, s2):
        """Create edit candidates and give Lev distance between them and arg oov.
           Lev dista computed with weights, given in constructor for class
           s1 is the candidate under consideration, s2 is the oov under study"""
        d = {}
        lenstr1 = len(s1)
        lenstr2 = len(s2)
        for i in xrange(-1,lenstr1+1):
            d[(i,-1)] = i+1
        for j in xrange(-1,lenstr2+1):
            d[(-1,j)] = j+1
        for i in xrange(lenstr1):
            for j in xrange(lenstr2):                
                d[(i,j)] = min(
                               d[(i-1,j)] + self.find_cost(s1[i], "zero"), # deletion
                               d[(i,j-1)] + self.find_cost("zero", s2[j]), # insertion
                               d[(i-1,j-1)] + self.find_cost(s1[i], s2[j]) # substitution
                              )     
        # TODO: make positive if work with positive values 
        return 0 - d[lenstr1-1,lenstr2-1]

    def set_ivdico(self, ivdico):
        """# TODO: Not coherent cos using ivdico for initiation"""
        self.ivdico = ivdico
