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
if "posp" in dir(): reload(posp)

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
import postprocessing as posp

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
    rerules = ppro.load_rules(tc.REGPREPRO)
    abbrules = ppro.load_rules(tc.ABBREVS)
    rinrules = ppro.load_rules(tc.RUNIN)
    if "dc_dico" not in dir(sys.modules["__main__"]):
        print "= prepro: Doubled-char dico, {}".format((time.asctime(time.localtime())))
        dc_dico = ppro.create_doubledchar_dico()
        print "Done {0}".format((time.asctime(time.localtime())))
    else:
        print "= prepro: Skip creating doubled-char dico"
    ppro.set_doubledchar_dico(dc_dico)
    if "ivs" not in dir(sys.modules["__main__"]):
        print "= prepro: Hashing IV dico, {0}".format(time.asctime(time.localtime()))
        ivs = ppro.generate_known_words()
        print "Done {0}".format(time.asctime(time.localtime()))
    else:
        print "= editor: Skip creating IV dico"
    ppro.set_ivdico(ivs)
    return ppro, safe_rules, rerules, abbrules, rinrules

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
    # Safetokens found
    safecorr = ppro.find_safetoken(oov.form, safe_rules)
    if safecorr is not False and safecorr["applied"] is True:
        oov.set_safecorr(safecorr["corr"])
        tweet.set_par_corr(safecorr["corr"], posi=oov.posi)
    # No safetokens
    if oov.safecorr is None:
        # Regexes 
        ppro_recorr = ppro.find_rematch(oov.form, rerules)
        oov.set_ppro_recorr_IV(ppro_recorr["IVflag"])
        if ppro_recorr["applied"] is True:
            if oov.ppro_recorr_IV:
                tweet.set_par_corr(ppro_recorr["corr"], posi=oov.posi)                
            oov.set_ppro_recorr(ppro_recorr["corr"])
        # Abbreviations
        if oov.ppro_recorr is not None:
            pprobase = oov.ppro_recorr
        else:
            pprobase = oov.form
        abbrev = ppro.find_prepro_general(pprobase, abbrules)
        if abbrev["applied"] is True:
            oov.set_abbrev(abbrev["corr"])
        # Run-in Rules
        runin = ppro.find_prepro_general(pprobase, rinrules)
        if runin["applied"] is True:
            oov.set_runin(runin["corr"])    

def create_edit_candidates(oov):
    """Create and score edit-candidates obtained with regexes and with edit-distance"""
    # TODO: correct side-effects of regexes

    # hash for regex-based candidates
    rgx_corr_cand_forms = {}

    # Determine form to base edit-candidates on    
    if oov.safecorr is None:
        if oov.ppro_recorr is None:
            oov.set_edbase(oov.form)
        else:
            oov.set_edbase(oov.ppro_recorr)

        # Regex-based -------------------
        #TODO: some side-effects of regexes, treat them (list-based if need be)
        rgx_corr_cands = edimgr.rgdist(oov.edbase) #edbase, not oov.form
        if len(rgx_corr_cands["cands"]) > 0:
            for rcc in rgx_corr_cands["cands"]:
                recando = editor.Candidate(rcc)
                # rgx_corr_cands: distances indexed by cand
                recando.set_dista(rgx_corr_cands["cands"][rcc])
                recando.set_candtype("re")
                oov.add_cand(recando)
            rgx_corr_cand_forms[oov.form] = True

        # Lev Distance based -----------
        lev_corr_cands = edimgr.generate_candidates(oov.edbase)
        if len(lev_corr_cands) > 0:
            for lcc in lev_corr_cands:
                if lcc == oov.form:
                    #Q: why were there cases like this at all? (ca. 6)
                    continue
                if lcc == oov.edbase:
                    continue
                # skip cand-object creation if regex-based dista exists for cand
                if lcc in rgx_corr_cand_forms:
                    continue
                levcando = editor.Candidate(lcc)
                #levcando.set_dista(edimgr.levdist(lcc, oov.form))
                levcando.set_dista(edimgr.levdist(lcc, oov.edbase))
                levcando.set_candtype("lev")
                oov.add_cand(levcando)

def find_lm_scores(oov):
    """Compute and set LM logprobs for <oov>'s candidates, and also for oov.form itself
       and oov.edbase"""
    global lgr
    if tc.increment_norm:
        lmlcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.par_corr])
    else:
        lmlcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.toks])
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
        if oov.edbase is not None:
            if slmmgr.check_is_inLM(oov.edbase):
                oov.set_edbase_lmsco(slmmgr.find_logprog_in_ctx(oov.edbase, lmlcon))

def cand_scorer(orca, scoretype="cand"):
    """Score OOV or candidate <orca> given distance (not for OOV)
       and lm scores and their weights. Cands with lmsco None
       will be filtered later, so ok to return a score for them."""
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
    """Rank based on edit-distance and LM scores"""
    global lgr
    if oov.has_cands:
        for cand in oov.cands:
            cand.dislmsco = cand_scorer(cand)
        if oov.form == oov.edbase:
            lgr.debug("RK_START: O [{0}], LM {1}, EB_SAME".format(repr(oov.form), oov.lmsco))
        else:
            lgr.debug("RK_START: O [{0}], LM {1}, EB [{2}], LM {3}".format(repr(oov.form), oov.lmsco,
                                                                 repr(oov.edbase), oov.edbase_lmsco))
        # Filter and rank with dist + lm
            # Compare >=, since using negative distances
        oov.cands_filtered = [cand for cand in oov.cands if cand.dista >= tc.maxdista
                              and cand.form != oov.form and cand.lmsco is not None]
        oov.ed_filtered_ranked = sorted(oov.cands_filtered,
                                        key=lambda x: x.dislmsco, reverse=True)
        lgr.debug("FltED Ranked {0}".format([rc.form for rc in oov.ed_filtered_ranked]))

        # Compare oov.lmsco, oov.edbase_lmsco and lmsco for best candidate
        if len(oov.ed_filtered_ranked) > 0:
            #if oov.edbase == 'si' and tweet.tid == '318707630908534784': #DEBUG
            #    import pdb
            #    pdb.set_trace()
            if oov.lmsco >= oov.edbase_lmsco:
                oov.assess_edbase = False
                if oov.form == oov.edbase:
                    reason = "LM_NoPre"
                else:
                    reason = "LM"
                if oov.lmsco >= oov.ed_filtered_ranked[0].lmsco: #oov
                    oov.keep_orig = True
                    lgr.debug(("O [{0}], LM {1} >> EB [{2}], LM {3} & >> Cmax [{4}], LM {5}, "+\
                              "Keeping OOV, Reason [{6}]").format(repr(oov.form), oov.lmsco,
                                                                repr(oov.edbase), oov.edbase_lmsco, 
                                                                repr(oov.ed_filtered_ranked[0].form),
                                                                oov.ed_filtered_ranked[0].lmsco, reason))
                else: #cand
                    oov.keep_orig = False
                    oov.best_ed_cando = oov.ed_filtered_ranked[0]
                    lgr.debug("+ OOV [{0}], BestEdCand [{1}], {2}, Reason [D+LMvsOOV]".format(
                        repr(oov.form), repr(oov.best_ed_cando.form), repr(oov.best_ed_cando.dislmsco)))
                    # partial correction
                    tweet.set_par_corr(oov.best_ed_cando.form, oov.posi)
            else: 
                oov.keep_orig = False
                if oov.edbase_lmsco >= oov.ed_filtered_ranked[0].lmsco: #edbase (if IV later??)
                    # assess_edbase can only be true when edbase is not equal to form
                    oov.assess_edbase = True
                    if oov.assess_edbase is True and oov.edbase == oov.form:
                        print "!! ERROR: assess_edbase when edbase equals form".format(
                            oov.edbase, oov.form, tweet.tid)
                    lgr.debug(("O [{0}], LM {1} << EB [{2}], LM {3} >> Cmax [{4}], LM {5}, "+\
                              "Assess Edbase, Reason [D+LMvsEB]").format(
                        repr(oov.form), oov.lmsco, repr(oov.edbase), oov.edbase_lmsco,
                        repr(oov.ed_filtered_ranked[0].form), oov.ed_filtered_ranked[0].lmsco))
                    # partial correction
                       # if check edbase IV status can read final forms from par_corr?
                    tweet.set_par_corr(oov.edbase, oov.posi)
                else:
                    oov.assess_edbase = False
                    oov.best_ed_cando = oov.ed_filtered_ranked[0]
                    lgr.debug("+ OOV [{0}], BestEdCand [{1}], {2}, Reason [D+LMvsEB]".format(
                        repr(oov.form), repr(oov.best_ed_cando.form), repr(oov.best_ed_cando.dislmsco)))
                    # partial correction
                    tweet.set_par_corr(oov.best_ed_cando.form, oov.posi)
            # log scores for each candidate
            for cand in oov.ed_filtered_ranked:
                lgr.debug("O [{0}], C [{1}], ED {2}| LM {3}| T {4}".format(
                    string.ljust(repr(oov.form), 15),
                    string.ljust(repr(cand.form), 15),
                    string.rjust(str(cand.dista), 4),
                    string.rjust(str(cand.lmsco), 15),
                    string.rjust(str(cand.dislmsco), 15)))
        else:
            oov.ed_filtered_ranked = []
            lgr.debug("+ OOV [{0}], No Edit Cands, Reason: [Filtering]".format(repr(oov.form)))
    else:
        oov.ed_filtered_ranked = []
        lgr.debug("+ OOV [{0}], No Edit Cands, Reason: [No IV Intersection]".format(repr(oov.form)))

def hash_final_form(oov, outdico, tweet):
    """Choose among edbase, oov.form and best candidate form given OOV instance state"""
    #if oov.edbase == 'si' and tid == '318707630908534784': #DEBUG
    #if tid == '318707630908534784':
    #    import pdb
    #    pdb.set_trace()
    if oov.assess_edbase:
        lgr.debug("WR O [{0}], Using the EB [{1}]".format(oov.form, oov.edbase))
        oov.edbase_posp = posp.recase(oov.form, oov.edbase, tweet)
        outdico[tweet.tid].append((oov.form, oov.edbase_posp))
    elif oov.keep_orig:
        outdico[tweet.tid].append((oov.form, oov.form))
    else:
        oov.best_ed_cando_posp = posp.recase(oov.form, oov.best_ed_cando.form, tweet)
        outdico[tweet.tid].append((oov.form, oov.best_ed_cando_posp))                    

def populate_outdico(all_tweeto, outdico):
    """Select candidates for final output filling a hash with them"""
    for tid in all_tweeto:
        tweet = all_tweeto[tid]
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok
            if oov.safecorr is not None:
                oov.safecorr_posp = posp.recase(oov.form, oov.safecorr, tweet)
                outdico[tid].append((oov.form, oov.safecorr_posp))
            elif oov.ppro_recorr is not None:
                oov.ppro_recorr_posp = posp.recase(oov.form, oov.ppro_recorr, tweet)
                # if verify IV status above could read from par_corr?
                if oov.ppro_recorr_IV:
                    outdico[tid].append((oov.form, oov.ppro_recorr_posp))
                else:
                    if tc.accept_all_IV_regex_outputs:
                        outdico[tid].append((oov.form, oov.ppro_recorr_posp))                    
                    elif len(oov.ed_filtered_ranked) > 0:
                        hash_final_form(oov, outdico, tweet)
                    else:
                        outdico[tid].append((oov.form, oov.form))
            else:
                if len(oov.ed_filtered_ranked) > 0:
                    hash_final_form(oov, outdico, tweet)
                else:
                    outdico[tid].append((oov.form, oov.form))          
    return outdico

def write_out(corr_dico):
    """Write out the final hash"""
    with codecs.open(tc.id_order, "r", "utf8") as idor:
        orderlist = [idn.strip() for idn in idor.readlines()]    
    with codecs.open(tc.OUTFN.format(prep.find_run_id()), "w", "utf8") as outfh:
        for tid in orderlist:
            if tid in corr_dico:
                outfh.write("%s\n" % tid)
                for oov_corr in corr_dico[tid]:
                    outfh.write("\t%s\t%s\n" % (oov_corr[0], oov_corr[1]))

def write_to_cumulog(clargs=None):
    """Write config infos and accuracy measures to cumulative log"""
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
    inf["increment_norm"] = tc.increment_norm
    inf["accept_all_IV_regex_outputs"] = tc.accept_all_IV_regex_outputs
    outhead = "Run ID [{0}], RevNum [{1}] {2}\n".format(inf["run_id"], inf["revnum"], "="*50)
    with codecs.open(tc.EVALFN.format(prep.find_run_id()), "r", "utf8") as done_res:
        with codecs.open(tc.CUMULOG, "a", "utf8") as cumu_res:
            cumu_res.write(outhead)
            cumu_res.write("RunComment: {}\n".format(inf["run_comment"]))
            for key in ["maxdista", "distaw", "lmw", "lmpath", "increment_norm"]:
                cumu_res.write("{}: {}\n".format(key, inf[key]))
            cumu_res.write("".join(done_res.readlines()[-4:]))

    
# MAIN =========================================================================

def main():

    global lgr
    global tweet
    global clargs
    global ref_OOVs # debug
    global all_tweets # debug
    global safe_rules
    global rerules
    global abbrules
    global rinrules
    global ppro
    global edimgr
    global outdico
    all_tweets = [] # debug
    
    # prep ---------------------------------------------------------------------
    lgr, lfh, clargs = preliminary_preps()
    
    # processing ---------------------------------------------------------------
    print "Start {0}".format(time.asctime(time.localtime()))
    print "Run ID: %s" % prep.find_run_id()
    lgr.info("Run {0} START | Rev [{1}] {2}".format(tc.RUNID, prep.find_git_revnum(), "="*60))

    print "= main: preliminary preps"
    id_order = prep.find_id_order()
    ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
    textdico = prep.grab_texts(tc.TEXTS)

    call_freeling(textdico)

    print "= main: load analyzers"
    ppro, safe_rules, rerules, abbrules, rinrules = load_preprocessing()
    edimgr = load_distance_editor()
    slmmgr, binslm = load_lm()

    print "= twittero: creating Tweet instances"
    all_tweeto, outdico = parse_tweets(textdico)

    print "= main: create baseline"
    baseline_dico = get_baseline_results(all_tweeto)

    print "= main: NORMALIZATION"
    x = 0 
    for tid in all_tweeto:
        lgr.debug("NORMALIZING, TID [{0}]".format(tid))
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
            print("Done {0} tweets, {1}".format(x, time.asctime(time.localtime())))

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

    print "End {0}".format(time.asctime(time.localtime()))
    
if __name__ == "__main__":
    #profile.run("main()")
    main()
