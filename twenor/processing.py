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
import subprocess
import sys
import time

import profile

# app-specific imports =========================================================

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
import edcosts
import lmmgr

# aux functions ================================================================

def set_option_parser():
    parser = argparse.ArgumentParser(prog='processing.py')
    parser.add_argument("-t", "--tag", action="store_true", help="tag with FreeLing")
    parser.add_argument("-c", "--comment", help="comment for run (shown in cumulog.txt)")
    parser.add_argument("-b", "--baseline", action="store_true",  help="baseline run: accept all OOV")
    args = parser.parse_args()
    return args

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


# MAIN =========================================================================

def main():

    global tweet
    global clargs
    global ref_OOVs # debug
    global all_tweets # debug
    global safe_rules # debug
    global ppro # debug
    global edi # debug
    all_tweets = [] # debug
    
    # prep ---------------------------------------------------------------------
    # logger
    logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
    lgr, lfh = prep.set_log(__name__, logfile_name, False)

    # cl options
    clargs = set_option_parser()
    if clargs is not None and clargs.tag:
        tc.TAG = True
    elif clargs is not None and not clargs.tag:
        tc.TAG = False

    # processing ---------------------------------------------------------------
    print "Start {}".format(time.asctime(time.localtime()))
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

    # prepare pre-processing ---------------------------------------------------
    ppro = ppr.Prepro()
    safe_rules = ppro.load_safetokens()
    rerules = ppro.load_regexes()
    global dc_dico
    if "dc_dico" not in dir(sys.modules["__main__"]):
        print "= prepro: Doubled-char dico, {}".format((time.asctime(time.localtime())))
        dc_dico = ppro.create_doubledchar_dico()
        print "Done {}".format((time.asctime(time.localtime())))
    else:
        print "= prepro: Skip creating doubled-char dico"
    #Q: need to set here cos recreating ppro above?
    ppro.set_doubledchar_dico(dc_dico)

    # prepare edit-distance modules --------------------------------------------
        # prepare cost-matrix first cos Editor needs it for initiation
    lev_score_mat = editor.EdScoreMatrix(edcosts)
    lev_score_mat.read_cost_matrix()
    lev_score_mat.find_matrix_stats()
    global lev_score_mat_hash #debug
    lev_score_mat_hash = lev_score_mat.create_matrix_hash()
        # can initiate Editor now
    global ivs
    edimgr = editor.EdManager(lev_score_mat_hash, tc.IVDICO)
    # don't recreate IV dico if in dir for this module
    if "ivs" not in dir(sys.modules["__main__"]):
        print "= editor: Hashing IV dico, {}".format(time.asctime(time.localtime()))
        ivs = edimgr.generate_and_set_known_words()
        print "Done {}".format(time.asctime(time.localtime()))
    else:
        print "= editor: Skip creating IV dico"
    #Q: need to set here cos recreating edi above?
    edimgr.set_ivdico(ivs)
    edimgr.prep_alphabet()

    # prepare LM module --------------------------------------------------------
    global slmmgr #debug
    global binslm #debug
    slmmgr = lmmgr.SLM()
    if not "binslm" in dir(sys.modules["__main__"]):
        binslm = slmmgr.create_bin_lm()
    else:
        print "= LM: Skip creating binary LM"
    slmmgr.set_slmbin(binslm)

    # read text and token tags into Tweet and Token objects --------------------
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
                # Q: This (below) was set as set_par_corr(tweet.toks)
                #    *Bad idea*, cos this creates identity of reference
                #    between tweet.toks and tweet.par_corr (just a new label for same ref)
                #    and then when altering tweet.par_corr (below) i was altering
                #    tweet.toks unwittingly.
                #    Since the *list contains objects*, use deepcopy
            # Copy the token-list so that .toks is not altered when altering .par_corr
            tweet.set_par_corr(copy.deepcopy(tweet.toks))
            all_tweets.append(tweet) #debug
        # baseline-populate output dico ---------------------------------------
        for tok in tweet.toks:
            # better than tok.isOOV cos no ref. vs. found err w isinstance
            if isinstance(tok, OOV):
                baseline_dico[tid].append((tok.form, tok.form))
        # PRE-PROCESSING =======================================================
        logmes = {"st":0, "re":0, "ab":0}
        for tok in tweet.toks:
            if not isinstance(tok, OOV):
                continue
            oov = tok # oov label easier            
            if logmes["st"] == 0:
                lgr.debug("# Safetokens #")
                logmes["st"] = 1
            # Safetokens -------------------------------------------------------
            #if tid == u'319028060852740099':
            #    import pdb
            #    pdb.set_trace()
            safecorr = ppro.find_safetoken(oov.form, safe_rules)
            # TODO: instead of these tuples, can i add attributes so that i can access
            #       whether safecorr applied by attribute, not by an index the existence of which
            #       i'll forget in a couple days?
            if safecorr is not False and safecorr[1] is True:
                oov.set_safecorr(safecorr[0])
                tweet.set_par_corr(safecorr[0], posi=oov.posi)
            # Regexes ----------------------------------------------------------
            if logmes["re"] == 0:
                lgr.debug("# Regexes #")
                logmes["re"] = 1
              # only if not safecorr for token
            if oov.safecorr is None:
                recorr = ppro.find_rematch(oov.form, rerules)
                if recorr[1] is True:
                    oov.set_recorr(recorr[0])
            # TODO: check here if recorr is IV, if so, see if accept or what
            #       or, at least, see if the form to base edit-candidates on
            #       should be the regex-preprocessed one (likely, since regexes
            #       remove v. unlikely sequences), or the original oov.
            #       Likely the regex-preprocessed, cos we're not introducing garbage
            #       with them, rather, removing them. 
            
            # EDIT CANDIDATES ==================================================            
            re_corr_forms = {} # TODO: correct side-effects of regexes
            if oov.safecorr is None and oov.recorr is None:
                # Regex-based
                #TODO: some side-effects of regexes, treat them (list-based if need be)
                re_corr_cands = edimgr.redist(oov.form)
                if len(re_corr_cands[0]) > 0:
                        # recorr[1] has how many times a rule has applied to a cand, for logging
                    for rcc in re_corr_cands[0]:
                        recando = editor.Candidate(rcc)
                        recando.set_dista(re_corr_cands[0][rcc])
                        recando.set_candtype("re")
                        oov.add_cand(recando)
                    #print tweet.tid, oov.form, recando.form, recando.dista
                    re_corr_forms[oov.form] = True
                # Lev Distance based
                #if oov.form == 'boorroh' or tid == '318742118996774913':
                #    import pdb
                #    pdb.set_trace()
                if oov.form not in re_corr_forms:
                    lev_corr_cands = edimgr.generate_candidates(oov.form)
                    if len(lev_corr_cands) > 0:
                        for lcc in lev_corr_cands:
                            levcando = editor.Candidate(lcc)
                            levcando.set_dista(edimgr.levdist(lcc, oov.form))
                            levcando.set_candtype("lev")
                            oov.add_cand(levcando)
                # rank candidates
                if oov.set_has_cands():
                #if len(oov.cands) > 0:
                    someLMCand = False
                    for cand in oov.cands:
                        cand_in_lm = cand.is_inLM(binslm)
                        if cand_in_lm:
                            lmlcon = slmmgr.find_left_context(oov.posi, [tok.form for tok in tweet.toks])
                            lmsco = slmmgr.find_logprog_in_ctx(cand.form, lmlcon)
                            cand.set_lmsco(lmsco)
                            cand.set_lmctxt(lmlcon)
                            someLMCand = True
                            oov.set_has_LM_cands(someLMCand)
                    ranked_candos = sorted(oov.cands, key=lambda x: x.dista, reverse=True)
                    ranked_filtered = [cand for cand in ranked_candos if cand.dista >= -1.5]
                    lgr.debug("Ranked {}".format([rc.form for rc in ranked_candos]))
                    if len(ranked_filtered) > 0:
                        oov.cands_ranked = ranked_filtered
                        oov.bestedcando = ranked_filtered[0]
                        lgr.debug("OOV [{}], BestEdCand [{}]".format(repr(oov.form), repr(oov.bestedcando.form)))
                    else:
                        oov.cands_ranked = []
                        lgr.debug("OOV [{}], No Edit Cands".format(repr(oov.form)))
                else:
                    oov.cands_ranked = []
                    lgr.debug("OOV [{}], No Edit Cands".format(repr(oov.form)))
                
            # POPULATE OUTDICO =================================================
            #if oov.form.lower().startswith("ibra"):
            #    import pdb
            #    pdb.set_trace()
            if oov.safecorr is not None:
                outdico[tid].append((oov.form, oov.safecorr))
            elif oov.recorr is not None:
                outdico[tid].append((oov.form, oov.recorr))
            elif len(oov.cands_ranked) > 0:
                outdico[tid].append((oov.form, oov.bestedcando.form))
            else:
                outdico[tid].append((oov.form, oov.form))                    

        lgr.info("@ Done @")

        if x % 100 == 0:
            print "Done {} tweets, {}".format(x, time.asctime(time.localtime()))
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

    print "End {}".format(time.asctime(time.localtime()))
    
if __name__ == "__main__":
    #profile.run("main()")
    main()
