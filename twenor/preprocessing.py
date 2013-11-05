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
blanklines = tc.BLANKLINES_RE

def create_doubledchar_dico():
    """Create a dico with IV words that contained doubled characters,
       if dico not in environment already"""    
    if not "doubledchar_dico" in dir():
        doubledchar_file = codecs.open(tc.doubledchar_dico, "r", "utf8")
        print "= Prepro: Creating doubledchar_dico"
        lgr.info("= Creating doubledchar_dico")
        doubledchar_dico = defaultdict(lambda: 1)
        for line in doubledchar_file:
            doubledchar_dico[line.rstrip()] #unicodes utf8-decoded
    else:
        print "+ Skip creating doubledchar_dico"
        lgr.info("+ Skip creating doubledchar_dico")


# Run safetokens before anything else
def load_safetokens():
    """Parse safelist tokens, that can be promoted as-is to output"""
    infile = tc.SAFETOKENS
    inlines = codecs.open(infile, "r", "utf8").readlines()
    safetokens = []
    safetoken_rules = []
    for line in inlines:
        if line.startswith("#") or re.match(blanklines, line):
            continue
        sline = line.strip().split("\t")
        if len(sline) >= 3:
            rule = [sline[0], re.compile(r"%s" % sline[1], re.IGNORECASE), sline[2]]
            safetoken_rules.append(rule)
        else:
            safetoken_rules.append([sline[0], sline[1]])
    return safetoken_rules

def find_safetoken(oov, rules):
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
                    lgr.debug("> OOV: |%s| Matched Rgx (gr0) Safetoken |%s| Gives |%s| ~ [Rule %s]" %\
                              (oov, match.group(0), rule[2], rule[0]))
                #TODO: add a third type: ^SU, where you re.sub??
                else:
                    #safe[2] is correct
                    corr = rule[2]
                    applied = True
                    lgr.debug("> OOV: |%s| Matched Rgx (gr0) Safetoken |%s| Gives |%s| ~ [Rule %s]" %\
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
                lgr.debug("> OOV: |%s| Matched Str Safetoken ~ |%s| ~ [Rule %s]" % \
                          (oov, match.group(0), rule[0]))
    return (corr, applied)

