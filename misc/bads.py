def cf_with_ent_2(oov):
    """Compare oov instance's befent with an entity-candidate
       based on the entity lists"""

    if oov.edbase is None:
        base = oov.form
    else:
        base = oov.edbase
    ent_status = entmgr.find_entity(oov.form)
    if ent_status["applied"]:
        oov.entcand = ent_status["corr"]
        lgr.debug("EN entcand [{0}] for O [{1}]".format(repr(oov.entcand), repr(oov.form)))
    else:
        oov.entcand = None
    extra_entities = [cand.form for cand in entmgr.add_entity_candidates(oov.form)]
    if oov.entcand is None:
        all_ents = extra_entities
    else:       
        extra_entities.extend([oov.entcand])
        all_ents = extra_entities
    all_ents = set(all_ents)
    oov.entcands = all_ents
    lgr.debug("EN all_ents {0}".format(repr(all_ents)))
    best_choice = oov.befent
    lgr.debug("EN best_choice [{0}] from oov.befent".format(repr(best_choice)))
    # lm context
    lcon = slmmgr.find_left_context(oov.posi, [t.form for t in tweet.par_corr])
    lgr.debug("EN lcon {0}".format(repr(lcon)))
    # look for befent in lm
    if slmmgr.check_is_inLM(oov.befent):
        lgr.debug("EN oov.befent [{0}] is in model".format(repr(oov.befent)))
        best_sco = slmmgr.find_logprog_in_ctx(oov.befent, lcon) * tc.lmw
        lgr.debug("EN oov.befent lmsco [{0}]".format(best_sco))
    # iterate over entity candidates
    if len(all_ents) > 0:
        no_info = True
        no_ent_in_lm = True
        set_both = False
        cands_to_compare = []
        for curcand in all_ents:
            if slmmgr.check_is_inLM(oov.befent) and slmmgr.check_is_inLM(curcand):
                lgr.debug("EN both oov.befent [{0}] and curcand [{1}]".format(repr(oov.befent), repr(curcand)))
                #lcon = slmmgr.find_left_context(oov.posi, [t.form for t in tweet.par_corr])
                befent_lmsco = slmmgr.find_logprog_in_ctx(oov.befent, lcon)
                lgr.debug("EN oov.befent lmsco [{0}]".format(befent_lmsco))
                curcand_lmsco = slmmgr.find_logprog_in_ctx(curcand, lcon) * tc.lmw
                lgr.debug("EN curcand_lmsco [{0}]".format(curcand_lmsco))
                curcand_dista = edimgr.levdist(curcand, base) * tc.distaw
                lgr.debug("EN curcand_dista [{0}]".format(curcand_dista))
                if curcand_lmsco + curcand_dista > best_sco:
                    lgr.debug("EN curcand_lmsco + dista > best_sco || [{0}] > [{1}]".format(curcand_lmsco + curcand_dista, best_sco))
                    best_choice = curcand
                    lgr.debug("EN best_choice []".format(repr(curcand)))                              
                    best_sco = curcand_lmsco + curcand_dista
                    set_both = True
                no_info = False
            elif slmmgr.check_is_inLM(oov.befent) and not slmmgr.check_is_inLM(curcand):
                no_info = False
                continue
            elif not slmmgr.check_is_inLM(oov.befent) and slmmgr.check_is_inLM(curcand):
                cands_to_compare.append(curcand)
                no_info = False
                no_ent_in_lm = False
            else:
                oov.aftent = oov.befent
                continue
        if no_info:
            oov.aftent = oov.entcand
        elif len(cands_to_compare) > 0 and not set_both:
            max_cand_sco = slmmgr.find_logprog_in_ctx(cands_to_compare[0], lcon) * tc.lmw + \
                           edimgr.levdist(cands_to_compare[0], base) * tc.distaw
            best_ent_cand = cands_to_compare[0]
            for cand in cands_to_compare[1:]:
                cand_sco = slmmgr.find_logprog_in_ctx(cand, lcon) * tc.lmw + \
                           edimgr.levdist(cand, base) * tc.distaw      
                if cand_sco > max_cand_sco:
                    max_cand_sco = cand_sco
                    best_ent_cand = cand
            best_choice = best_ent_cand
            oov.aftent = best_choice
        else:
            oov.aftent = oov.befent
    else:
        oov.aftent = oov.befent


    #if type(inp) in [type(""), type(u"")] and not os.path.isfile(inp):
    #    comstr = "echo -e %s | sudo %s %s >%s" % (inp.encode("utf8"), tc.ANACLI, port, outfn)
    #    print comstr

    def generate_candidates(self, word):
        """Return IV edit-candidates up to two edit-operations
           Based on Norvig's "correct" function"""
        candidates = self.known([word]).\
                     union(self.known(self.edits1(word))).\
                     union(self.known_edits2(word))
        lgr.debug("++ All generated candidates: |%s| |%s|" % (word, repr(sorted(list(candidates)))))
        return candidates

##        generated_known2 = set(e2.decode("utf8") for e1 in self.edits1(word)
##                               for e2 in self.edits1(e1)
##                               if e2 in self.ivdico and type(e2) is str)

##        generated_known2 = set(e2 if e2 in self.ivdico
##                               for e1 in self.edits1(word)
##                               for e2 in self.edits1(e1))

##def cand_scorer(form, scoretype="cand"):
##    """Score candidate given distance and lm scores and their weights"""
##    if form.lmsco is None:
##        form.lmsco = 0
##    if scoretype == "cand":
##        return form.dista * tc.distaw + form.lmsco * tc.lmw
##    if scoretype == "oov":
##        return form.lmsco * tc.lmw       



                if tc.accept_all_IV_regex_outputs:
                    if oov.ppro_recorr_IV:
                        outdico[tid].append((oov.form, oov.ppro_recorr))
                    else:
                        outdico[tid].append((oov.form, oov.form))
                else:
                    # new wf
                    if oov.ppro_recorr_IV:
                        # oov.edbase is synonym with oov.ppro_recorr
                        if len(oov.ed_filtered_ranked) > 0:
                            if oov.assess_edbase:
                                outdico[tid].append((oov.form, oov.edbase))
                            else:
                                outdico[tid].append((oov.form, oov.best_ed_cando.form))
                        else:
                            outdico[tid].append((oov.form, oov.edbase))
                    else:
                        if len(oov.ed_filtered_ranked) > 0:
                            outdico[tid].append((oov.form, oov.best_ed_cando.form))
                        else:
                            outdico[tid].append((oov.form, oov.form))                       
            else:
                if len(oov.ed_filtered_ranked) > 0:
                    if oov.keep_orig:
                        outdico[tid].append((oov.form, oov.form))
                    else:
                        outdico[tid].append((oov.form, oov.best_ed_cando.form))
                else:
                    outdico[tid].append((oov.form, oov.form))






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
        lgr.debug("EN NO entcand for [{0}]".format(repr(oov.form))
                  
    if oov.entcand is not None:
        if (oov.safecorr is not None or oov.abbrev is not None or
            oov.runin is not None or oov.ppro_recorr_IV is True):
            oov.aftent = oov.befent
        else:
            if oov.befent.lower() in stpwords:
                oov.aftent = oov.befent
            befent_dista = edimgr.levdist(oov.befent, oov.edbase)
            if befent_dista >= -0.5:
                if oov.befent != oov.edbase:
                    oov.aftent = oov.befent
                elif oov.entcand is not None:
                    oov.aftent = oov.entcand
                else:
                    oov.aftent = oov.befent
            else:
                oov.aftent = oov.entcand




            # caps variations
            if corr.isupper():                
                if corr in self.ivdico or corr.lower() in self.ivdico:
                    IVflag = True
                    corr = corr.lower()
                else:
                    IVflag = False
            elif corr[0].isupper() and not corr.isupper():
                if corr in self.ivdico or corr.lower() in self.ivdico:
                    IVflag = True            
                else:
                    IVflag = False
            elif corr in self.ivdico:
                IVflag = True
            else:
                IVflag = False
            lgr.debug("RE Out, OOV [{0}], recorr [{1}] , IVFlag [{2}], [RE_Changed]".format(
                repr(oov), repr(corr), IVflag))
        else:
            IVflag = None
