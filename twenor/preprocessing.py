#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import codecs
import logging
from collections import defaultdict
import os
import re

import preparation as prep
import tnconfig as tc

# logging
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
lgr, lfh = prep.set_log(__name__, logfile_name)

# globals
#blanklines = tc.BLANKLINES_RE

class Prepro:
    def __init__(self):
        pass
    
    blanklines = tc.BLANKLINES_RE
    doubledchar_dico = None

    def create_doubledchar_dico(self):
        """Create a dico with IV words that contained doubled characters"""
        doubledchar_file = codecs.open(tc.doubledchar_dico, "r", "utf8")
        lgr.info("= Creating doubledchar_dico")
        doubledchar_dico = defaultdict(lambda: 1)
        for line in doubledchar_file:
            doubledchar_dico[line.rstrip()] #unicodes utf8-decoded
        self.set_doubledchar_dico(doubledchar_dico)
        return doubledchar_dico
    
    def load_safetokens(self, infile=tc.SAFETOKENS):
        """Parse safelist tokens, that can be promoted as-is to output"""
        inlines = codecs.open(infile, "r", "utf8").readlines()
        safetokens = []
        safetoken_rules = []
        for line in inlines:
            if line.startswith("#") or re.match(self.blanklines, line):
                continue
            sline = line.strip().split("\t")
            if len(sline) >= 3:
                rule = [sline[0], re.compile(r"%s" % sline[1], re.IGNORECASE), sline[2]]
                safetoken_rules.append(rule)
            else:
                safetoken_rules.append([sline[0], sline[1]])
        return safetoken_rules

    def find_safetoken(self, oov, rules):
        """Check oov against safetoken rules"""
        corr = oov
        applied = False
        for rule in rules:
            # regex-type rules
            if type(rule) is list and len(rule) > 2: 
                # regex rule types, by ID: "^MA" vs. other. "^MA" mean group(0) is the correct form
                match = re.match(rule[1], oov)
                if match:
                    #group(0) is the correct form
                    if str(rule[0][0:2]) in ["MA", "ma"]:
                        corr = match.group(0)
                        applied = True
                        lgr.debug("ST OOV |%s| Matched Rgx (gr0) Safetoken |%s| Gives |%s| ~ [Rule %s]" %\
                                  (oov, match.group(0), rule[2], rule[0]))
                    #TODO: add a third type: ^SU, where you re.sub??
                    else:
                        #safe[2] is correct
                        corr = rule[2]
                        applied = True
                        lgr.debug("ST OOV |%s| Matched Rgx (gr0) Safetoken |%s| Gives |%s| ~ [Rule %s]" %\
                                  (oov, match.group(0), rule[2], rule[0]))    
            # token-type rules
            else:
                match = re.match(re.compile(rule[1], re.IGNORECASE), oov)
                if not match:
                    continue
                if match.group(0) != oov:
                    lgr.error("!! Regex Bad: Should Match |%s| ~ Matches |%s| ~  Rule [%s]" %\
                               (oov, match.group(0), rule[0]))
                    return False
                else:
                    corr = oov
                    applied = True
                    lgr.debug("ST OOV |%s| Matched Str Safetoken ~ |%s| ~ [Rule %s]" % \
                              (oov, match.group(0), rule[0]))
        return (corr, applied)

    def load_regexes(self, infile=tc.REGPREPRO):
        """Load regexes that will be used to correct OOVs
           Rule format: ^id\tcontext\treplacement\t(comment)$"""
        inlines = codecs.open(infile, "r", "utf8").readlines()
        rules = []
        for line in inlines:
            if line.startswith("#") or re.match(self.blanklines, line):
                continue
            sline = line.strip().split("\t")
            rule = [sline[0], re.compile(sline[1], re.IGNORECASE), sline[2]]
            rules.append(rule)
        return rules

    def find_rematch(self, oov, rules):
        # mbe should take the safe dico as argument
        """Check OOV against regexes. Rules are from a utf8 file
           utf8 decoded and so are dico contents, so can run as-is """
        # apply rules sequentially and recursively
        applied = False
        corr = oov
        for rule in rules:
            if int(rule[0]) >= 9000: # rules for a second phase
                continue
            corr_before = corr
            corr = re.sub(rule[1], rule[2], corr)
            if corr != corr_before: # rule has changed it
                # rather than doubledchar_dico maybe the choice should be:
                # if corr_before IV and corr not IV, take corr_before
                # requires accessing the IV dico from here
                if not corr_before in self.doubledchar_dico:
                    lgr.debug("RE Ph1, Initial: [%s], Before: [%s], After: [%s] || Rule [%s]: [%s]" % \
                                  (oov, corr_before, corr, rule[0], repr([rule[1].pattern, rule[2]])))
                    applied = True
                else:
                    # revert rule application
                    lgr.debug("REVERT Ph1, Initial: [%s], Before: [%s], After: [%s] || Rule [%s]: [%s], Reason [%s] OOV" % \
                                  (oov, corr_before, corr, rule[0], repr([rule[1].pattern, rule[2]]), corr))
                    corr = corr_before
        #return (corr, applied)

        # phase 2 of rules
        # 1. delete doubled characters not deleted by previous rules, unless word in a safelist
        ph1corr = corr # bkp ph1 corr output as ph1 corr
        for rule in rules:
            if int(rule[0]) >= 9000:
                corr_before = corr
                if not corr_before in self.doubledchar_dico:
                    corr = re.sub(rule[1], rule[2], corr)
                    if corr != corr_before:
                        applied = True
                        lgr.debug("RE Ph2, Initial: [%s], Ph1: [%s], Before: [%s], After: [%s] || Rule [%s]: [%s]" % \
                                      (oov, ph1corr, corr_before, corr, rule[0], repr([rule[1].pattern, rule[2]])))
                else:
                    lgr.debug("RE Ph2 NOT applying to |%s| , |%s|: is in doubledchar_dico" % (ph1corr, corr_before))
        return (corr, applied)

    def set_doubledchar_dico(self, dc):
        self.doubledchar_dico = dc
        

