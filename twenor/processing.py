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

from nltk.corpus import stopwords

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
if "edcosts" in dir(): reload(edcosts)
if "generic_edcosts" in dir(): reload(generic_edcosts)
if "lmmgr" in dir(): reload(lmmgr)
if "posp" in dir(): reload(posp)
if "entities" in dir(): reload(entities)
if "tnstats" in dir(): reload(tnstats)

import tnconfig as tc
import preparation as prep
import freelmgr as fl
import twittero
from twittero import Tweet, Token, OOV
import neweval as neval
import preprocessing as ppr
import editor
import edcosts
import generic_edcosts
import lmmgr
import postprocessing as posp
import entities
import tnstats

# functions ================================================================

def set_option_parser():
    """Set option parser and return command-line arguments"""
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
    if clargs.tag is not None and clargs.tag:
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
        print "= FL: Tagging with Freeling, {0}".format(time.asctime(time.localtime()))
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
        print "= prepro: Doubled-char dico, {0}".format((time.asctime(time.localtime())))
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

def load_entities():
    """Prepare entity-hashes"""
    global ent_hash
    entity_config = ppro.find_ent_files_active()
    ppro.set_ent_files_active(entity_config)
    if "ent_hash" not in dir(sys.modules["__main__"]):
        print "= prepro: Hashing entity files, {0}".format(time.asctime(time.localtime()))
        ent_hash = ppro.hash_entity_files()
        print "Done, {0}".format(time.asctime(time.localtime()))
        return ent_hash
    else:
        print "= prepro: Skip creating entity-hashes"
    return sys.modules[__name__].ent_hash

def merge_iv_and_entities(ivs, ent_hash):
    """Add entities to the IV dico"""
    global ivs_only
    ivs_only = copy.deepcopy(ivs)
    for key in ent_hash:
        if key not in ivs:
            ivs[key] = 1
    print "+ IV dico length: {0}".format(len(ivs_only))
    print "+ IV + Entities dico length: {0}".format(len(ivs))
    return ivs

def load_distance_editor():
    """Instantiate EdScoreMatrix and EdManager instances, returning the latter"""
    global lev_score_mat_hash #debug
    global ivs

    # prepare cost-matrix first cos EdManager needs it for initiation
    if tc.generic_lev:
        chosen_edcosts = generic_edcosts
    else:
        chosen_edcosts = edcosts
    lev_score_mat = editor.EdScoreMatrix(chosen_edcosts)
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

def load_entity_manager(ent_hash, ivs, edimgr, lmmgr):
    """Instantiate the entity manager class"""
    #TODO: is a separate function necessary?
    entmgr = entities.EntityMgr(ent_hash, ivs, edimgr, lmmgr)
    return entmgr

##def check_entity_basic(oov, form, toktype="n/a"):
##    """Look for exact matches or case-variants for a form (str) in an entity-list,
##       and set properties in <oov> accordingly. <toktype> is for logging"""
##    #TODO: is it needed to give it an object? Refactoring?
##    ent_status = entmgr.find_entity(form, toktype)
##    if ent_status["applied"] is True:
##        oov.entifin = ent_status["corr"]
##        tweet.set_par_corr(oov.entifin, posi=oov.posi)
##        return True
##    return False

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
    if tc.safelist_end:
        return
    # No safetokens
    if oov.safecorr is None:
        #if ((not tc.safelist_end and not tc.abbrev_end and not tc.runin_end)
        #    or not tc.regex_end):
        if tc.use_regexes:
            # Regexes 
            ppro_recorr = ppro.find_rematch(oov.form, rerules)
            oov.set_ppro_recorr_IV(ppro_recorr["IVflag"])
            if ppro_recorr["applied"] is True:
                if oov.ppro_recorr_IV:
                    tweet.set_par_corr(ppro_recorr["corr"], posi=oov.posi)                
                oov.set_ppro_recorr(ppro_recorr["corr"])
        if tc.regex_end:
            return
        # Abbreviations
        if oov.ppro_recorr is not None:
            pprobase = oov.ppro_recorr
        else:
            pprobase = oov.form
        abbrev = ppro.find_prepro_general(pprobase, abbrules, ruletype="AB")
        if abbrev["applied"] is True:
            oov.set_abbrev(abbrev["corr"])
            tweet.set_par_corr(abbrev["corr"], posi=oov.posi)
        if tc.abbrev_end:
            return
        # Run-in Rules
        runin = ppro.find_prepro_general(pprobase, rinrules, ruletype="RI")
        if runin["applied"] is True:
            oov.set_runin(runin["corr"])    
            tweet.set_par_corr(runin["corr"], posi=oov.posi)

def create_edit_candidates(oov):
    """Create and score edit-candidates obtained with regexes and with edit-distance"""
    # TODO: correct side-effects of regexes

    # hash for regex-based candidates
    rgx_corr_cand_forms = {}

    # Determine form to base edit-candidates on    
    if oov.safecorr is None and oov.abbrev is None and oov.runin is None:
        if oov.ppro_recorr is None:
            oov.set_edbase(oov.form)
        else:
            oov.set_edbase(oov.ppro_recorr)
        lgr.debug("ED EB [{0}]".format(repr(oov.edbase)))

        # Regex-based -------------------
        #TODO: some side-effects of regexes, treat them (list-based if need be)
        if tc.context_sens_ed:
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
                    oov.accept_best_ed_cando = True
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
                    oov.accept_best_ed_cando = True
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
            #Q: is the if necessary? Or should the test be if oov.safecorr .... , forgetting generic_workflow test?
            if tc.generic_workflow:
                oov.keep_orig = True
            else:
                # checking for trusted variants added for indiv modules
                if oov.safecorr is None and oov.abbrev is None and oov.runin is None and oov.ppro_recorr is None:
                    oov.keep_orig = True
    else:
        oov.ed_filtered_ranked = []
        lgr.debug("+ OOV [{0}], No Edit Cands, Reason: [No IV Intersection]".format(repr(oov.form)))
        #Q: is the if necessary? Or should the test be if oov.safecorr .... , forgetting generic_workflow test?
        if tc.generic_workflow:
            oov.keep_orig = True
        else:
            # checking for trusted variants added for indiv modules
            if oov.safecorr is None and oov.abbrev is None and oov.runin is None and oov.ppro_recorr is None:
                oov.keep_orig = True

def rank_before_entities(oov):
    """Select best candidate before comparing with entities"""
    if oov.safecorr is not None:
        oov.befent = oov.safecorr
        lgr.debug("RK Befent [{0}] from safecorr [{1}]".format(repr(oov.befent), repr(oov.safecorr)))
    elif oov.abbrev is not None:
        oov.befent = oov.abbrev
        lgr.debug("RK Befent [{0}] from abbrev [{1}]".format(repr(oov.befent), repr(oov.abbrev)))
    elif oov.runin is not None:
        oov.befent = oov.runin
        lgr.debug("RK Befent [{0}] from runin [{1}]".format(repr(oov.befent), repr(oov.runin)))
    elif oov.ppro_recorr is not None and oov.ppro_recorr_IV:
        oov.befent = oov.ppro_recorr
        lgr.debug("RK Befent [{0}] from ppro [{1}]".format(repr(oov.befent), repr(oov.ppro_recorr)))
    elif oov.keep_orig:
        oov.befent = oov.form
        lgr.debug("RK Befent [{0}] from orig [{1}]".format(repr(oov.befent), repr(oov.form)))
    elif oov.assess_edbase:
        oov.befent = oov.edbase
        lgr.debug("RK Befent [{0}] from edbase [{1}]".format(repr(oov.befent), repr(oov.edbase)))
    elif oov.accept_best_ed_cando:
        lgr.debug("RK Befent [{0}] from best_ed_cando [{1}]".format(repr(oov.befent), repr(oov.best_ed_cando.form)))        
        oov.befent = oov.best_ed_cando.form
    # for cumulative/isolated improvements, option to accept oov.form if all else fails
    else:
        oov.befent = oov.form

def populate_easy(all_tweeto, outdico, order="aft"):
    """Select candidates for final output filling a hash with them"""
    for tid in all_tweeto:
        tweet = all_tweeto[tid]
        lgr.debug("POPULATE EASY FINAL DICO, TID [{0}]".format(tid))
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok
            if order == "aft":
                oov.aftent_posp = posp.recase(oov.form, oov.aftent, tweet)
                outdico[tid].append((oov.form, oov.aftent_posp))
                lgr.debug("WRF O [{0}], C [{1}]".format(
                    repr(oov.form), repr(oov.aftent_posp)))
            else:
                oov.befent_posp = posp.recase(oov.form, oov.befent, tweet)
                outdico[tid].append((oov.form, oov.befent_posp))
                lgr.debug("WRF O [{0}], C [{1}]".format(
                    repr(oov.form), repr(oov.befent_posp)))                
    return outdico

def cf_with_ent(oov):
    """Compare oov instance's befent with an entity-candidate
       based on the entity lists"""
    # mb should apply to oov.befent AND oov.form and see what returns 
    ent_status = entmgr.find_entity(oov.form)
    if ent_status["applied"]:
        oov.entcand = ent_status["corr"]
        lgr.debug("EN entcand [{0}] for O [{1}]".format(repr(oov.entcand), repr(oov.form)))
    else:
        oov.entcand = None
        oov.aftent = oov.befent
        lgr.debug("EN NO entcand for [{0}]".format(repr(oov.form)))
                  
    if oov.entcand is not None:
        if (oov.safecorr is not None or oov.abbrev is not None or
            oov.runin is not None or oov.ppro_recorr_IV is True):
            oov.aftent = oov.befent
            lgr.debug("EN keep befent, Reason [{0}] [Trusted corr]".format(repr(oov.befent)))
        else:
            #if oov.befent.lower() in stpwords:
            #    oov.aftent = oov.befent
            #    lgr.debug("EN keep befent, Reason [{0}] [Stopw]".format(repr(oov.befent)))
            # variable base_for_enti_dista allows to test entities module separately
            if not tc.use_ed and tc.use_entities:
                base_for_enti_dista = oov.form
            else:
                base_for_enti_dista = oov.edbase
            befent_dista = edimgr.levdist(oov.befent, base_for_enti_dista)
            #if befent_dista >= -0.5:
            #    if not oov.befent == base_for_enti_dista:
            #        oov.aftent = oov.befent
            #        lgr.debug("EN keep befent, Reason [{0}] vs. [{1}][Dista]".format(repr(oov.befent),
            #                                                                          repr(base_for_enti_dista)))
            #    else:
            #        lcon = slmmgr.find_left_context(oov.posi, [t.form for t in tweet.par_corr])
            #        befent_lmsco = slmmgr.find_logprog_in_ctx(oov.befent, lcon)
            #        entcand_lmsco = slmmgr.find_logprog_in_ctx(oov.entcand, lcon)
            #        if befent_lmsco >= entcand_lmsco:
            #            oov.aftent = oov.befent
            #        else:
            #            oov.aftent = oov.entcand
            #else:
            #    oov.aftent = oov.entcand
            #    lgr.debug("EN keep aftent [{0}], vs. befent [{1}], O [{2}]".format(repr(oov.aftent),
            #                                                                       repr(base_for_enti_dista),
            #                                                                       repr(oov.form)))
            if befent_dista < -0.5:
                oov.aftent = oov.entcand
            else:
                if slmmgr.check_is_inLM(oov.befent) and slmmgr.check_is_inLM(oov.entcand):
                    if tc.increment_norm:
                        lcon = slmmgr.find_left_context(oov.posi, [t.form for t in tweet.par_corr])
                    else:
                        lcon = slmmgr.find_left_context(oov.posi, [t.form for t in tweet.toks])                        
                    befent_lmsco = slmmgr.find_logprog_in_ctx(oov.befent, lcon)
                    entcand_lmsco = slmmgr.find_logprog_in_ctx(oov.entcand, lcon)
                    if befent_lmsco >= entcand_lmsco:
                        oov.aftent = oov.befent
                    else:
                        oov.aftent = oov.entcand
                elif slmmgr.check_is_inLM(oov.befent) and not slmmgr.check_is_inLM(oov.entcand):
                    oov.aftent = oov.befent
                else:
                    oov.aftent = oov.entcand

def hash_final_form(oov, outdico, tweet):
    """Choose among edbase, oov.form and best candidate form given OOV instance state"""
    if oov.assess_edbase:
        lgr.debug("WR O [{0}], Using the EB [{1}]".format(oov.form, oov.edbase))
        oov.edbase_posp = posp.recase(oov.form, oov.edbase, tweet)
        outdico[tweet.tid].append((oov.form, oov.edbase_posp))
        lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
            repr(oov.form), repr(oov.edbase_posp), "EB||Orig||BC"))
    elif oov.keep_orig:
        outdico[tweet.tid].append((oov.form, oov.form))
        lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
            repr(oov.form), repr(oov.form), "Orig||EB||BC"))
    else:
        oov.best_ed_cando_posp = posp.recase(oov.form, oov.best_ed_cando.form, tweet)
        outdico[tweet.tid].append((oov.form, oov.best_ed_cando_posp))
        lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
        repr(oov.form), repr(oov.best_ed_cando_posp), "BC||EB||Orig"))
                  
def populate_outdico(all_tweeto, outdico):
    """Select candidates for final output filling a hash with them"""
    for tid in all_tweeto:
        tweet = all_tweeto[tid]
        lgr.debug("POPULATE FINAL DICO, TID [{0}]".format(tid))
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok
            if oov.safecorr is not None:
                oov.safecorr_posp = posp.recase(oov.form, oov.safecorr, tweet)
                outdico[tid].append((oov.form, oov.safecorr_posp))
                lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                    repr(oov.form), repr(oov.safecorr_posp), "ST"))
            elif oov.entifin is not None:
                outdico[tid].append((oov.form, oov.entifin))                
                lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                    repr(oov.form), repr(oov.entifin), "EN_1"))
                # next if entifin
                continue
            elif oov.abbrev is not None:
                oov.abbrev_posp = posp.recase(oov.form, oov.abbrev, tweet)
                outdico[tid].append((oov.form, oov.abbrev_posp))
                lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                    repr(oov.form), repr(oov.abbrev_posp), "AB"))
            elif oov.runin is not None:
                oov.runin_posp = posp.recase(oov.form, oov.runin, tweet)
                outdico[tid].append((oov.form, oov.runin_posp))
                lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                    repr(oov.form), repr(oov.runin_posp), "RI"))                
            elif oov.ppro_recorr is not None:
                oov.ppro_recorr_posp = posp.recase(oov.form, oov.ppro_recorr, tweet)
                # if verify IV status above could read from par_corr?
                if oov.ppro_recorr_IV:
                    outdico[tid].append((oov.form, oov.ppro_recorr_posp))
                    lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                        repr(oov.form), repr(oov.ppro_recorr_posp), "PRE-IV"))
                else:
                    if tc.accept_all_IV_regex_outputs:
                        outdico[tid].append((oov.form, oov.ppro_recorr_posp))
                        lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                            repr(oov.form), repr(oov.ppro_recorr_posp), "PRE-Accept-All"))
                    elif len(oov.ed_filtered_ranked) > 0:
                        hash_final_form(oov, outdico, tweet)
                    else:
                        outdico[tid].append((oov.form, oov.form))
            else:
                if len(oov.ed_filtered_ranked) > 0:
                    hash_final_form(oov, outdico, tweet)
                else:
                    outdico[tid].append((oov.form, oov.form))
                    lgr.debug("WRF O [{0}], C [{1}], T [{2}]".format(
                        repr(oov.form), repr(oov.form), "Orig-Default"))
    return outdico

def add_extra_entities():
    """Add extra entities for consideration with LM"""
    global all_tweeto
    for tid in all_tweeto:
        lgr.debug("ADDING MORE ENTITIES, TID [{}]".format(tid))
        tweet = all_tweeto[tid]
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok
            # basing entity-candidates on the pre-processed variant if available
            if oov.edbase is None:
                entity_candidates = [cand.form for cand in
                                     entmgr.add_entity_candidates(oov.form)]
            else:
                entity_candidates = [cand.form for cand in
                                     entmgr.add_entity_candidates(oov.edbase)]
            # not sure why some candidates started with lowercase
            entity_candidates = [cand for cand in entity_candidates if
                                 cand[0].isupper()]
            if oov.entcand is not None:
                entity_candidates.append(oov.entcand)
            oov.entcands = entity_candidates

def write_out(corr_dico):
    """Write out the final hash in a format that matches reference output format"""
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
    global golden_set_res
    global all_tweeto
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
    inf["generic_lev"] = tc.generic_lev
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
    inf["merge_iv_and_entities"] = tc.merge_iv_and_entities
    inf["accent_check_in_regexes"] = tc.accent_check_in_regexes
    if tc.EVAL:
        inf["corpus"] = "test"
    else:
        inf["corpus"] = "dev"

    golden_set_res = tnstats.hash_gold_standard(tc.ANNOTS)
    coverage_info, coverage_stats = tnstats.get_upper_bound(golden_set_res, all_tweeto.values())
    envs_dico = {"W": "work", "H": "home", "S": "hslt-server"}
    inf["enviro"] = envs_dico[tc.ENV]
    wf_dico = {True: "lm_all", False: "lm_one"}
    inf["lm_app"] = wf_dico[tc.use_lmall]
    outhead = "== Run ID [{0}], RevNum [{1}] {2}\n".format(inf["run_id"], inf["revnum"], "="*48)
    with codecs.open(tc.EVALFN.format(prep.find_run_id()), "r", "utf8") as done_res:
        with codecs.open(tc.CUMULOG, "a", "utf8") as cumu_res:
            cumu_res.write(outhead)
            cumu_res.write("RunComment: {0}\n".format(inf["run_comment"]))
            for key in ["enviro", "corpus", "lm_app",
                        "generic_lev", "maxdista", "distaw", "accent_check_in_regexes",
                        "lmw", "lmpath", "increment_norm",
                        "accept_all_IV_regex_outputs", "merge_iv_and_entities"]:
                cumu_res.write("- {0}: {1}\n".format(key, inf[key]))
            iso_cumu_settings_list = ['tc.no_postprocessing', 'tc.activate_prepro',
                                     'tc.safelist_end', 'tc.abbrev_end', 'tc.use_regexes',
                                     'tc.use_ed', 'tc.context_sens_ed', 'tc.use_entities']
            iso_cumu_settings_dict = dict((name, eval(name)) for name in iso_cumu_settings_list)
            cumu_res.write("+ Isolating/Cumulative Module Settings +\n")
            for setting in iso_cumu_settings_dict:
                cumu_res.write("- {0}: {1}\n".format(setting, iso_cumu_settings_dict[setting]))
            cumu_res.write("+ Upper Bound +\n")
            for stat in coverage_stats:
                cumu_res.write("- {0}: {1}\n".format(stat, coverage_stats[stat]))
                             
            cumu_res.write("".join(done_res.readlines()[-4:]))
            done_res.seek(0,0)
        print "+ Results +"
        print "".join(done_res.readlines()[-4:])

    
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
    global ivs
    global ent_hash
    global entmgr
    global ppro
    global edimgr
    global stpwords
    global outdico
    global all_tweeto
    all_tweets = [] # debug
    
    # prep ---------------------------------------------------------------------
    lgr, lfh, clargs = preliminary_preps()
    
    # processing ---------------------------------------------------------------

    # Check if need to delete in-memory IV and entities dicos (if just changed config)
    #ok = raw_input("Need to reset the IV dictionary (if changed tc.merged_iv_and_entities)? [y] to reset\n")
    #if ok == "y":
    #    print "- Deleting 'ivs' (Imerged IV + ent) in current scope"
    #    delattr(sys.modules[__name__], "ivs")
    #    if "ivs_only" in dir(sys.modules["__main__"]):
    #        print "- Deleting 'ivs_only' (IV) in current scope"
    #        delattr(sys.modules[__name__], "ivs_only")

    corpusname = {True: "test", False: "dev"}
    print "Corpus: {0}".format(corpusname[tc.EVAL])
    print "Comment: {0}".format(tc.COMMENT)

    print "Start {0}".format(time.asctime(time.localtime()))
    print "Run ID: %s" % prep.find_run_id()
    try:
        lgr.info("Run {0} START | Rev [{1}] {2}".format(tc.RUNID, prep.find_git_revnum(), "="*60))
    except OSError:
        lgr.info("Run {0} START | Rev [{1}] {2}".format(tc.RUNID, "XXXX", "="*60))

    print "= main: preliminary preps"
    id_order = prep.find_id_order()
    ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
    textdico = prep.grab_texts(tc.TEXTS)

    call_freeling(textdico)

    print "= main: load analyzers"
    ppro, safe_rules, rerules, abbrules, rinrules = load_preprocessing()
    ent_hash = load_entities()
    if tc.merge_iv_and_entities:
        ivs = merge_iv_and_entities(ivs, ent_hash)
    edimgr = load_distance_editor()
    slmmgr, binslm = load_lm()
    entmgr = load_entity_manager(ent_hash, ivs, edimgr, lmmgr)
    stpwords = stopwords.words('english')

    print "= twittero: creating Tweet instances"
    all_tweeto, outdico = parse_tweets(textdico)

    print "= main: create baseline"
    baseline_dico = get_baseline_results(all_tweeto)

    if not tc.BASELINE:
        print "= main: NORMALIZATION"
        x = 0 
        for tid in all_tweeto:
            lgr.debug("NORMALIZING, TID [{0}]".format(tid))
            tweet = all_tweeto[tid]
            for tok in tweet.toks:
                if not isinstance(tok, OOV):
                    continue
                oov = tok # easier label
                if tc.activate_prepro:
                    # separate prepro components switched on/off inside preprocess(oov)
                    preprocess(oov)
                if tc.use_ed:
                    create_edit_candidates(oov)
                    find_lm_scores(oov)
                rank_candidates(oov)
                rank_before_entities(oov)
                if tc.use_entities:
                    cf_with_ent(oov)
            x += 1
            #if x == 10: break #debug

            if x % 100 == 0:
                print("Done {0} tweets, {1}".format(x, time.asctime(time.localtime())))

        # Extra step to add more entity candidates
        if tc.use_lmall:
            print "= Adding extra entities, {0}".format(time.asctime(time.localtime()))
            add_extra_entities()
            print "= Done"

        #outdico = populate_outdico(all_tweeto, outdico) # old, now use populate_easy

        if tc.generic_workflow or tc.use_entities: # Doesn't cover all cases. Enough for paper-tests
            wf = "aft"
        else:
            wf = "bef"
        outdico = populate_easy(all_tweeto, outdico, wf)

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
