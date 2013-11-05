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

def load_safetokens(infile=tc.SAFETOKENS):
    """Parse safelist tokens, that can be promoted as-is to output"""
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

def load_regexes(infile=tc.REGPREPRO):
    """Load regexes that will be used to correct OOVs
       Rule format: ^id\tcontext\treplacement\t(comment)$"""
    inlines = codecs.open(infile, "r", "utf8").readlines()
    rules = []
    for line in inlines:
        if line.startswith("#") or re.match(blanklines, line):
            continue
        sline = line.strip().split("\t")
        rule = [sline[0], re.compile(sline[1], re.IGNORECASE), sline[2]]
        rules.append(rule)
    return rules

def find_rematch(oov, rules):
    # mbe should take the safe dico as argument
    # or group it all into a class, so that can have self.X() access to it <- lks cleanest
    """Check OOV against regexes. Rules are from a utf8 file
       utf8 decoded and so are dico contents, so can run as-is """
    # apply rules sequentially and recursively
    applied = False
    corr = oov
    for rule in rules:
        if int(rule[0]) >= 1000: # rules for a second phase
            continue
        corr_before = corr
        corr = re.sub(rule[1], rule[2], corr)
        if corr != corr_before: # rule has changed it
            lgr.debug("RE Ph1 | Initial: [%s], Before: [%s], After: [%s] || Rule [%s]: [%s]" % \
                          (oov, corr_before, corr, rule[0], repr([rule[1].pattern, rule[2]])))
            # here could prevent the 'leer' -> 'ler' case checking against doubledchar_dico
            applied = True
    return (corr, applied)

    # phase 2 of rules
    # 1. delete doubled characters unless word in a safelist
##    lgr.debug("## Rules Phase 2 ##")
##    for rule in rules:
##        if int(rule[0]) >= 1000:
##            initial_oov = prepro_oov
##            if not initial_oov in doubledchar_dico:
##                prepro_oov = re.sub(rule[1], rule[2], prepro_oov)
##                if prepro_oov != initial_oov:
##                    lgr.debug("Applied Ph2 Rule %s || Before: |%s| || After: |%s|" % \
##                          (repr([rule[0], rule[1].pattern, rule[2]]), initial_oov, prepro_oov))
##                    ppd = True
##                    if not (initial_oov, prepro_oov) in ppd_list:
##                        ppd_list.append((initial_oov, prepro_oov))
##            else:
##                lgr.debug("Ph2 NOT applying to |%s|: is in doubledchar_dico" % initial_oov)
##            
##    prepros = ((prepro_oov, orig_oovs[key][count][0][1]), orig_oovs[key][count][1], "ppd=%s" % ppd)
##    prepro_oovs[key].append(prepros)
##    count += 1
##    lgr.debug("> Done Regex Preprocessing candidate |%s|" % oov[0][0])
##    return (prepro_oovs, ppd_list)

