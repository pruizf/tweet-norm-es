#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import inspect
import logging
import os
import pprint
import re
import shutil
import subprocess
import sys
import time

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
 
# app-specific imports
import tnconfig as tc
import preparation as prep
import freelmgr as fl
from twittero import Tweet, Token, OOV
import neweval as neval

# aux functions

def write_out(corr_dico):
    with codecs.open(tc.OUTFN, "w", "utf8") as outfh:
        for tid in corr_dico:
            outfh.write("%s\n" % tid)
            for oov_corr in corr_dico[tid]:
                outfh.write("\t%s\t%s\n" % (oov_corr[0], oov_corr[1]))

# MAIN -------------------------------------------------------------------------
if __name__ == "__main__":
    # logger
    logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % tc.RUNID)
    lgr, lfh = prep.set_log(__name__, logfile_name)

    # processing
    lgr.info("Run {0} START {1}".format(tc.RUNID, "="*70))
    id_order = prep.find_id_order()
    ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
    textdico = prep.grab_texts(tc.TEXTS)
    # start Freeling server if not running
    if not fl.check_server(tc.fl_port):
        fl.start_server()
    # tag texts with Freeling
    if not os.path.exists(tc.TAGSDIR):
        os.makedirs(tc.TAGSDIR)
    if tc.TAG:
        fl.tag_texts(textdico)

    # read text and token tags into Tweet and Token objects
    all_tweeto = {}
    baseline_dico = {}
    out_dico = {}
    x = 0
    for tid in textdico:
        x += 1
        # dico for final outputs
        baseline_dico[tid] = []
        out_dico[tid] = []
        if "%s.tags" % tid not in os.listdir(tc.TAGSDIR):
            lgr.error("Missing tags for %s" % tid)
        # create tweet objs
        all_tweeto[tid] = Tweet(tid, textdico[tid])
        tweet = all_tweeto[tid]
        # add OOVs if applies
        tweet.find_OOV_status(ref_OOVs)
        if tweet.hasOOVs:
            tweet.set_ref_OOVs(ref_OOVs[tid])
            tweet.find_toks_and_OOVs()
            tweet.cf_OOVs_found_vs_ref()
        # baseline-populate output dico
        for tok in tweet.toks:
            if tok.isOOV:
                baseline_dico[tid].append((tok.form, tok.form))
        if x == 999:
            break

    # write results
    lgr.info("Writing out")
    #chosen_out_dico = out_dico
    chosen_out_dico = baseline_dico
    write_out(chosen_out_dico)
    # write eval
    lgr.info("Running evaluation")
    neval.main(tc.ANNOTS, tc.OUTFN)

    lgr.removeHandler(lfh)
    
