#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import argparse
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
if "prep" in dir(): reload(prep)
if "fl" in dir(): reload(fl)
if "twittero" in dir(): reload(twittero)
if "ppro" in dir(): reload(ppr)
if "editor" in dir(): reload(editor)

import tnconfig as tc
import preparation as prep
import freelmgr as fl
import twittero
from twittero import Tweet, Token, OOV
import neweval as neval
import preprocessing as ppr
import editor

# aux functions

def set_option_parser():
    parser = argparse.ArgumentParser(prog='processing.py')
    parser.add_argument("-t", "--tag", action="store_true", help="tag with FreeLing")
    parser.add_argument("-c", "--comment", help="comment for run (shown in cumulog.txt)")
    parser.add_argument("-b", "--baseline", action="store_true",  help="baseline run: accept all OOV")
    args = parser.parse_args()
    return args

def write_out(corr_dico):
    with codecs.open(tc.OUTFN.format(prep.find_run_id()), "w", "utf8") as outfh:
        for tid in corr_dico:
            outfh.write("%s\n" % tid)
            for oov_corr in corr_dico[tid]:
                outfh.write("\t%s\t%s\n" % (oov_corr[0], oov_corr[1]))

def write_to_cumulog(clargs=None):
    inf = {}
    inf["run_id"] = prep.find_run_id()
    inf["revnum"] = prep.find_git_revnum()
    if clargs.comment is not None and clargs.comment != "":
        inf["run_comment"] = clargs.comment
    else:
        inf["run_comment"] = tc.COMMENT
    outhead = "Run ID [{0}], RevNum [{1}] {2}\n".format(inf["run_id"], inf["revnum"], "="*50)
    with codecs.open(tc.EVALFN.format(prep.find_run_id()), "r", "utf8") as done_res:
        with codecs.open(tc.CUMULOG, "a", "utf8") as cumu_res:
            cumu_res.write(outhead)
            cumu_res.write("RunComment: {}\n".format(inf["run_comment"]))
            cumu_res.write("".join(done_res.readlines()[-4:]))


# MAIN -------------------------------------------------------------------------

def main():

    global tweet
    global clargs
    global all_tweets # debug
    global safe_rules # debug
    global ppro # debug
    global edi # debug
    all_tweets = []
    
    # logger
    logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
    lgr, lfh = prep.set_log(__name__, logfile_name, False)

    # cl options
    clargs = set_option_parser()
    if clargs is not None and clargs.tag:
        tc.TAG = True
    elif clargs is not None and not clargs.tag:
        tc.TAG = False

    # processing
    print "Run ID: %s" % prep.find_run_id()
    lgr.info("Run {0} START | Rev [{1}] {2}".format(tc.RUNID, prep.find_git_revnum(), "="*60))
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

    # prepare pre-processing
    ppro = ppr.Prepro()
    safe_rules = ppro.load_safetokens()
    rerules = ppro.load_regexes()
    global dc_dico
    if "dc_dico" not in dir(sys.modules["__main__"]):
        print "= prepro: Doubled-char dico"
        dc_dico = ppro.create_doubledchar_dico()
    #Q: need to set here cos recreating ppro above?
    ppro.set_doubledchar_dico(dc_dico)

    # prepare edit-distance modules
    global ivs
    edi = editor.Editor("", tc.IVDICO)
    # don't recreate IV dico if in dir for this module
    if "ivs" not in dir(sys.modules["__main__"]):
        print "= editor: Hashing IV dico"
        ivs = edi.generate_and_set_known_words()
    #Q: need to set here cos recreating edi above?
    edi.set_ivdico(ivs)

    # read text and token tags into Tweet and Token objects
    all_tweeto = {}
    baseline_dico = {}
    outdico = {}
    x = 0
    for tid in textdico:
        # prep =================================================================
        lgr.info("# Start [%s] #" % tid)
        x += 1
        # dico for final outputs
        baseline_dico[tid] = []
        outdico[tid] = []
        if "%s.tags" % tid not in os.listdir(tc.TAGSDIR):
            lgr.error("Missing tags for %s" % tid)
        # create tweet objs ====================================================
        all_tweeto[tid] = Tweet(tid, textdico[tid])
        tweet = all_tweeto[tid]
        # add OOVs if applies
        tweet.find_OOV_status(ref_OOVs)
        if tweet.hasOOVs:
            tweet.set_ref_OOVs(ref_OOVs[tid])
            tweet.find_toks_and_OOVs()
            tweet.cf_OOVs_found_vs_ref()
            tweet.set_par_cor(tweet.toks)
            all_tweets.append(tweet) #debug
        # baseline-populate output dico ---------------------------------------
        for tok in tweet.toks:
            # better than tok.isOOV cos no ref. vs. found err w isinstance
            if isinstance(tok, OOV):
                baseline_dico[tid].append((tok.form, tok.form))
        # pre-processing =======================================================
        logmes = {"st":0, "re":0, "ab":0}
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok # oov label easier            
            if logmes["st"] == 0:
                lgr.debug("# Safetokens #")
                logmes["st"] = 1
            # safetokens -------------------------------------------------------
            safecorr = ppro.find_safetoken(oov.form, safe_rules)
            if safecorr is not False and safecorr[1] is True:
                oov.set_safecorr(safecorr[0])
                tweet.set_par_cor(safecorr, posi=oov.posi)
            # regexes ----------------------------------------------------------
            if logmes["re"] == 0:
                lgr.debug("# Regexes #")
                logmes["re"] = 1
              # only if not safecorr for token
            if oov.safecorr is None:
                recorr = ppro.find_rematch(oov.form, rerules)
                if recorr[1] is True:
                    oov.set_recorr(recorr[0])
            # edit candidates ==================================================
            if oov.safecorr is None and oov.safecorr is None:
                #TODO: some side-effects of regexes, treat them (list-based if need be)
                edcorr = edi.redist(oov.form)
                if len(edcorr) > 0:
                    print oov.form, edcorr
            
            # populate outdico =================================================
            if oov.safecorr is not None:
                outdico[tid].append((oov.form, oov.safecorr))
            elif oov.recorr is not None:
                outdico[tid].append((oov.form, oov.recorr))
            else:
                outdico[tid].append((oov.form, oov.form))                    

        lgr.info("@ Done @")
        if x == 999:
            break

    # write results
    lgr.info("Writing out")
    if tc.BASELINE:
        chosen_outdico = baseline_dico
    else:
        chosen_outdico = outdico
    write_out(chosen_outdico)
    # write eval
    lgr.info("Running evaluation")
    neval.main(tc.ANNOTS, tc.OUTFN.format(prep.find_run_id()))
    write_to_cumulog(clargs=clargs)

    lgr.removeHandler(lfh)
    
if __name__ == "__main__":
    main()
