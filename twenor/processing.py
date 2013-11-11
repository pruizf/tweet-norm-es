#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import argparse
import codecs
from collections import defaultdict
import copy
import inspect
import logging
import os
import pprint
import re
import shutil
import string
import subprocess
import sys
import time

# setup  =========================================================

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
if "tc" in dir(): reload(tc)
if "prep" in dir(): reload(prep)
if "fl" in dir(): reload(fl)
if "twittero" in dir(): reload(twittero)
if "ppro" in dir(): reload(ppr)
if "editor" in dir(): reload(editor)
if "lmmgr" in dir(): reload(lmmgr)

import tnconfig as tc
import preparation as prep
import freelmgr as fl
import twittero
from twittero import Tweet, Token, OOV
import neweval as neval
import preprocessing as ppr
import editor
import edcosts
import lmmgr

# functions ================================================================

def set_option_parser():
    parser = argparse.ArgumentParser(prog='processing.py')
    parser.add_argument("-t", "--tag", action="store_true", help="tag with FreeLing")
    parser.add_argument("-c", "--comment", help="comment for run (shown in cumulog.txt)")
    parser.add_argument("-b", "--baseline", action="store_true",  help="baseline run: accept all OOV")
    parser.add_argument("-x", "--maxdista", help="maximum edit distance above which candidate is filtered")
    parser.add_argument("-d", "--distaw", help="weight for edit-distance scores")
    parser.add_argument("-l", "--lmw", help="weight for language model scores")
    parser.add_argument("-p", "--lmpath", help="path to Arpa file for language model")
    parser.add_argument("-w", "--lm_window", help="left-window for context lookup in language model")
    args = parser.parse_args()
    return args

def preliminary_preps():
    """Set up logger and read command line arguments"""
    # logger
    logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
    lgr, lfh = prep.set_log(__name__, logfile_name, False)
    # cl options
    clargs = set_option_parser()
    if clargs is not None and clargs.tag:
        tc.TAG = True
    elif clargs is not None and not clargs.tag:
        tc.TAG = False
    #TODO: options below don't seem to be able to affect tc other than for writing to the cumulog
    elif clargs.maxdista is not None:
        tc.maxdista = clargs.maxdista
    elif clargs.distaw is not None:
        tc.distaw = clargs.distaw
    elif clargs.lmw is not None:
        tc.lmw = clargs.lmw
    return lgr, lfh, clargs

def call_freeling(textdico):
    """Check if needed to start freeling If so, tag texts with it"""
    # start Freeling server if not running
    if not fl.check_server(tc.fl_port):
        fl.start_server()
    # tag texts with Freeling
    if not os.path.exists(tc.TAGSDIR):
        os.makedirs(tc.TAGSDIR)
    if tc.TAG:
        print "= FL: Tagging with Freeling, {}".format(time.asctime(time.localtime()))
        fl.tag_texts(textdico)
    else:
         print"= FL: Skipping Freeling-tagging"

def load_preprocessing():
    """Return Rule-sets for safe-tokens, regex-based prepro and abbreviations
       TODO: abbreviations"""
    global dc_dico
    global ivs

    ppro = ppr.Prepro()
    safe_rules = ppro.load_safetokens()
    rerules = ppro.load_regexes()
    if "dc_dico" not in dir(sys.modules["__main__"]):
        print "= prepro: Doubled-char dico, {}".format((time.asctime(time.localtime())))
        dc_dico = ppro.create_doubledchar_dico()
        print "Done {}".format((time.asctime(time.localtime())))
    else:
        print "= prepro: Skip creating doubled-char dico"
    #Q: need to set here cos recreating ppro above?
    ppro.set_doubledchar_dico(dc_dico)

    # don't recreate IV dico if in dir for this module
    if "ivs" not in dir(sys.modules["__main__"]):
        print "= prepro: Hashing IV dico, {}".format(time.asctime(time.localtime()))
        ivs = ppro.generate_known_words()
        print "Done {}".format(time.asctime(time.localtime()))
    else:
        print "= editor: Skip creating IV dico"
    #Q: need to set here cos recreating ppro above?
    ppro.set_ivdico(ivs)
    return ppro, safe_rules, rerules

def load_distance_editor():
    """Instantiate EdScoreMatrix and EdManager instances, returning the latter"""
    global lev_score_mat_hash #debug
    global ivs

    # prepare cost-matrix first cos EdManager needs it for initiation
    lev_score_mat = editor.EdScoreMatrix(edcosts)
    lev_score_mat.read_cost_matrix()
    lev_score_mat.find_matrix_stats()
    lev_score_mat_hash = lev_score_mat.create_matrix_hash()
    # can initiate EdManager now
    edimgr = editor.EdManager(lev_score_mat_hash, ivs)
    edimgr.prep_alphabet()
    return edimgr

def load_lm():
    """Return lmmgr instance and binary lm, using pysrilm"""
    global slmmgr #debug
    global binslm #debug
    slmmgr = lmmgr.SLM()
    if not "binslm" in dir(sys.modules["__main__"]):
        binslm = slmmgr.create_bin_lm()
    else:
        print "= LM: Skip creating binary LM"
    slmmgr.set_slmbin(binslm)
    return slmmgr, binslm

def parse_tweets(textdico):
    """Create Tweet, Token and OOV instances. Prepare dico for final outputs"""
    global all_tweets # debug. For tests. The real wf is based on all_tweeto
    global lgr
    all_tweeto = {}
    outdico = {}
    for tid in textdico:
        # get Freeling-tags
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
            # Deepcopy token-objects to not change them when changing .par_corr
            tweet.set_par_corr(copy.deepcopy(tweet.toks))
            if type(tweet.par_corr) is not list:
                print "!! par_corr not list"
                import pdb
                pdb.set_trace()
            all_tweets.append(tweet) #debug
        outdico[tid] = []
    return all_tweeto, outdico

def get_baseline_results(all_tweeto):
    baseline_dico = {}
    for tid in all_tweeto:
        baseline_dico[tid] = []
        tweet = all_tweeto[tid]
        for tok in tweet.toks:
            # better than tok.isOOV, to keep ref. and found apart)
            if isinstance(tok, OOV):
                baseline_dico[tid].append((tok.form, tok.form))
    return baseline_dico

def preprocess(oov):
    global lgr
    global tweet
    global ppro
    # Safetokens -------------------------------------------------------
    safecorr = ppro.find_safetoken(oov.form, safe_rules)
    # TODO: instead of these tuples, can i add attributes so that i can access
    #       whether safecorr applied by attribute, not by a forgettable index
    if safecorr is not False and safecorr["applied"] is True:
        oov.set_safecorr(safecorr["corr"])
        tweet.set_par_corr(safecorr["corr"], posi=oov.posi)
    # Regexes ----------------------------------------------------------
      # only if not safecorr for token
    if oov.safecorr is None:
        ppro_recorr = ppro.find_rematch(oov.form, rerules)
        oov.set_ppro_recorr_IV(ppro_recorr["IVflag"])
        if ppro_recorr["applied"] is True:
            if oov.ppro_recorr_IV:
                tweet.set_par_corr(ppro_recorr["corr"], posi=oov.posi)                
            oov.set_ppro_recorr(ppro_recorr["corr"]) 

def create_edit_candidates(oov):
    """Create and score edit-candidates obtained with regexes and with edit-distance"""
       # TODO: correct side-effects of regexes

    # hash for regex-based candidates
    rged_cand_forms = {}

    # Determine form to base edit-candidates on    
    if oov.safecorr is None:
        if oov.ppro_recorr is None:
            edbase = oov.form
        else:
            edbase = oov.ppro_recorr
        oov.edbase = edbase

        # Regex-based -------------------
        #TODO: some side-effects of regexes, treat them (list-based if need be)
        rged_corr_cands = edimgr.rgdist(edbase) #edbase, not oov.form
        if len(rged_corr_cands["cands"]) > 0:
            for rcc in rged_corr_cands["cands"]:
                recando = editor.Candidate(rcc)
                # dista is value of hash rged_corr_cands, indexed by cand
                recando.set_dista(rged_corr_cands["cands"][rcc])
                recando.set_candtype("re")
                oov.add_cand(recando)
            rged_cand_forms[oov.form] = True

        # Lev Distance based -----------
        lev_corr_cands = edimgr.generate_candidates(oov.edbase)
        if len(lev_corr_cands) > 0:
            for lcc in lev_corr_cands:
                if lcc == oov.form:
                    #Q: why were there cases like this at all? (ca. 6)
                    continue
                if lcc == oov.edbase:
                    continue
                # skip cand-object creation if regex-based distance exists for cand
                if lcc in rged_cand_forms:
                    continue
                levcando = editor.Candidate(lcc)
                levcando.set_dista(edimgr.levdist(lcc, oov.form))
                levcando.set_candtype("lev")
                oov.add_cand(levcando)

def find_lm_scores(oov):
    """Compute and set LM logprobs for <oov>'s candidates, and also for oov.form itself"""
    global lgr
    #lmlcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.toks])
    lmlcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.par_corr])
    if oov.set_has_cands():
        someLMCand = False
        for cand in oov.cands:
            cand_in_lm = slmmgr.check_is_inLM(cand.form)
            if cand_in_lm:
                lmsco = slmmgr.find_logprog_in_ctx(cand.form, lmlcon)
                cand.set_lmsco(lmsco)
                cand.set_lmctx(lmlcon)
                cand.set_inLM(cand_in_lm)              
                someLMCand = True
                oov.set_has_LM_cands(someLMCand)
        if slmmgr.check_is_inLM(oov.form):
            oov.set_lmsco(slmmgr.find_logprog_in_ctx(oov.form, lmlcon))

def cand_scorer(orca, scoretype="cand"):
    """Score OOV or candidate <orca> given distance (not for OOV)
       and lm scores and their weights. Cands with lmsco None
       will be filtered later, so ok to return a score for them."""
    #if form.form == 'sic': # debug: test cases of lmsco is None
    #    import pdb
    #    pdb.set_trace()
    if orca.lmsco is not None:
        if scoretype == "cand":
            return orca.dista * tc.distaw + orca.lmsco * tc.lmw
        elif scoretype == "oov":
            return orca.lmsco * tc.lmw
    else:
        if scoretype == "cand":
            return orca.dista * tc.distaw
        elif scoretype == "oov":
            return None

def rank_candidates(oov):
    global lgr
    oov.best = None
    
    if oov.lmsco is not None:
        oov.wlmsco = cand_scorer(oov, scoretype="oov")

    # TODO: begins to be crap
    if oov.edbase is not None:
        if slmmgr.check_is_inLM(oov.edbase):
            edbase_lcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.toks])
            oov.edbase_lmsco = slmmgr.find_logprog_in_ctx(oov.edbase, edbase_lcon)

    # TODO: more examples of crap
    use_edbase = False
    oov.edbase_best = False
    if oov.lmsco <= oov.edbase_lmsco:
        use_edbase = True
    lgr.debug("RK use_edbase is {}: edbase, LM {}| oov, LM {}, ".format(use_edbase, oov.edbase_lmsco, oov.lmsco))

    if oov.has_cands:
        for cand in oov.cands:
            cand.dislmsco = cand_scorer(cand)
        # use >=, since using negative distances
        oov.cands_filtered = [cand for cand in oov.cands
                              if cand.dista >= tc.maxdista
                              and cand.form != oov.form
                              and cand.lmsco is not None]
        oov.ed_filtered_ranked = sorted(oov.cands_filtered,
                                        key=lambda x: x.dislmsco, reverse=True)
        lgr.debug("FltED Ranked {}".format([rc.form for rc in oov.ed_filtered_ranked]))
        if len(oov.ed_filtered_ranked) > 0:
            # Compare OOV LM score and edbase lm score
            if not use_edbase:
                if oov.lmsco >= oov.ed_filtered_ranked[0].lmsco:
                    oov.best = oov
                    #Q: why is this branch never visited now?
                    lgr.debug("O [{}], LM {} >> Cmax [{}], LM {}, Keeping OOV, Reason [LM]".format(
                        repr(oov.form), oov.lmsco, repr(oov.ed_filtered_ranked[0].form),
                        oov.ed_filtered_ranked[0].lmsco))
            else:
                if oov.edbase_lmsco >= oov.ed_filtered_ranked[0].lmsco:
                    oov.edbase_best = True
                    lgr.debug("O [{}], LM {} << EDBASE [{}], LM {} >> Cmax [{}], LM {}, Using Edbase, Reason [LM]".format(
                        repr(oov.form), oov.lmsco, repr(oov.edbase), oov.edbase_lmsco,
                        repr(oov.ed_filtered_ranked[0].form), oov.ed_filtered_ranked[0].lmsco))
                    # partial correction
                    tweet.set_par_corr(oov.edbase, oov.posi)
            for cand in oov.ed_filtered_ranked:
                lgr.debug("O [{0}], C [{1}], ED {2}| LM {3}| T {4}".format(
                    string.ljust(repr(oov.form), 15),
                    string.ljust(repr(cand.form), 15),
                    string.rjust(str(cand.dista), 4),
                    string.rjust(str(cand.lmsco), 15),
                    string.rjust(str(cand.dislmsco), 15)))
            if oov.best is None: # means some cand's lm score is better than the OOV's
                if not oov.edbase_best:
                    oov.best_ed_cando = oov.ed_filtered_ranked[0]
                    lgr.debug("+ OOV [{}], BestEdCand [{}], {}".format(
                        repr(oov.form), repr(oov.best_ed_cando.form), repr(oov.best_ed_cando.dislmsco)))
                    # partial correction
                    tweet.set_par_corr(oov.best_ed_cando.form, oov.posi)
                    
        else:
            oov.ed_filtered_ranked = []
            lgr.debug("+ OOV [{}], No Edit Cands, Reason: [Filtering]".format(repr(oov.form)))
    else:
        oov.ed_filtered_ranked = []
        lgr.debug("+ OOV [{}], No Edit Cands, Reason: [No IV Intersection]".format(repr(oov.form)))

def populate_outdico(all_tweeto, outdico):
    for tid in all_tweeto:
        tweet = all_tweeto[tid]
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok # oov label easier    
            if oov.safecorr is not None:
                outdico[tid].append((oov.form, oov.safecorr))
            elif oov.ppro_recorr is not None:
                if oov.ppro_recorr_IV:
                    outdico[tid].append((oov.form, oov.ppro_recorr))
                else:
                    #outdico[tid].append((oov.form, oov.form))
                    if len(oov.ed_filtered_ranked) > 0:
                        if oov.edbase_best:
                            lgr.debug("WR Using the edbase, [{}]".format(oov.edbase))
                            outdico[tid].append((oov.form, oov.edbase))
                        elif oov.best: # way to express that oov's LM score better than scor for any candidate
                            outdico[tid].append((oov.form, oov.form))
                        else:
                            outdico[tid].append((oov.form, oov.best_ed_cando.form))                    
                    else:
                        outdico[tid].append((oov.form, oov.form))
            else:
                if len(oov.ed_filtered_ranked) > 0:
                    if oov.edbase_best:
                        outdico[tid].append((oov.form, oov.edbase))
                    elif oov.best: # way to express that oov's LM score better than scor for any candidate
                        outdico[tid].append((oov.form, oov.form))
                    else:
                        outdico[tid].append((oov.form, oov.best_ed_cando.form))                    
                else:
                    outdico[tid].append((oov.form, oov.form))
              
    return outdico

def write_out(corr_dico):
    with codecs.open(tc.id_order, "r", "utf8") as idor:
        orderlist = [idn.strip() for idn in idor.readlines()]    
    with codecs.open(tc.OUTFN.format(prep.find_run_id()), "w", "utf8") as outfh:
        for tid in orderlist:
            if tid in corr_dico:
                outfh.write("%s\n" % tid)
                for oov_corr in corr_dico[tid]:
                    outfh.write("\t%s\t%s\n" % (oov_corr[0], oov_corr[1]))

def write_to_cumulog(clargs=None):
    inf = {}
    inf["run_id"] = prep.find_run_id()
    try:
        inf["revnum"] = prep.find_git_revnum()
    except OSError:
        print "- Can't get git revision number (OSError)"
        inf["revnum"] = "XXXXX"
    if clargs.comment is not None and clargs.comment != "":
        inf["run_comment"] = clargs.comment
    else:
        inf["run_comment"] = tc.COMMENT
    if clargs.maxdista is not None:
        inf["maxdista"] = clargs.maxdsita
    else:
        inf["maxdista"] = tc.maxdista
    if clargs.distaw is not None:
        inf["distaw"] = clargs.distaw
    else:
        inf["distaw"] = tc.distaw
    if clargs.lmw is not None:
        inf["lmw"] = clargs.lmw
    else:
        inf["lmw"] = tc.lmw
    if clargs.lmpath is not None:
        inf["lmpath"] = os.path.basename(clargs.lmpath)
    else:
        inf["lmpath"] = os.path.basename(tc.lmpath)
    if clargs.lm_window is not None:
        inf["lm_window"] = tc.lm_window
    else:
        inf["lm_window"] = tc.lm_window
    outhead = "Run ID [{0}], RevNum [{1}] {2}\n".format(inf["run_id"], inf["revnum"], "="*50)
    with codecs.open(tc.EVALFN.format(prep.find_run_id()), "r", "utf8") as done_res:
        with codecs.open(tc.CUMULOG, "a", "utf8") as cumu_res:
            cumu_res.write(outhead)
            cumu_res.write("RunComment: {}\n".format(inf["run_comment"]))
            for key in ["maxdista", "distaw", "lmw", "lmpath"]:
                cumu_res.write("{}: {}\n".format(key, inf[key]))
            cumu_res.write("".join(done_res.readlines()[-4:]))

    
# MAIN =========================================================================

def main():

    global tweet
    global clargs
    global ref_OOVs # debug
    global all_tweets # debug
    global safe_rules
    global rerules
    global ppro
    global edimgr
    global lgr
    all_tweets = [] # debug
    
    # prep ---------------------------------------------------------------------
    lgr, lfh, clargs = preliminary_preps()
    
    # processing ---------------------------------------------------------------
    print "Start {}".format(time.asctime(time.localtime()))
    print "Run ID: %s" % prep.find_run_id()
    lgr.info("Run {0} START | Rev [{1}] {2}".format(tc.RUNID, prep.find_git_revnum(), "="*60))

    print "= main: preliminary preps"
    id_order = prep.find_id_order()
    ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
    textdico = prep.grab_texts(tc.TEXTS)

    call_freeling(textdico)

    print "= main: load analyzers"
    ppro, safe_rules, rerules = load_preprocessing()
    edimgr = load_distance_editor()
    slmmgr, binslm = load_lm()

    print "= twittero: creating Tweet instances"
    all_tweeto, outdico = parse_tweets(textdico)

    print "= main: create baseline"
    baseline_dico = get_baseline_results(all_tweeto)

    print "= main: NORMALIZATION"
    x = 0 
    for tid in all_tweeto:
        lgr.debug("NORMALIZING, TID [{}]".format(tid))
        tweet = all_tweeto[tid]
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok # easier label
            preprocess(oov)
            create_edit_candidates(oov)
            find_lm_scores(oov)
            rank_candidates(oov)
        x += 1
        if x % 100 == 0:
            print("Done {} tweets, {}".format(x, time.asctime(time.localtime())))

    outdico = populate_outdico(all_tweeto, outdico)

    # write-out ----------------------------------------------------------------
    print "= writer"
    lgr.info("Writing out")
    if tc.BASELINE:
        chosen_outdico = baseline_dico
    else:
        chosen_outdico = outdico
    write_out(chosen_outdico)

    # evaluation ---------------------------------------------------------------
    print "= evaluation"
    lgr.info("Running evaluation")
    neval.main(tc.ANNOTS, tc.OUTFN.format(prep.find_run_id()))
    write_to_cumulog(clargs=clargs)

    lgr.removeHandler(lfh)

    print "End {}".format(time.asctime(time.localtime()))
    
if __name__ == "__main__":
    #profile.run("main()")
    main()
