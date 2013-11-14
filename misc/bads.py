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
