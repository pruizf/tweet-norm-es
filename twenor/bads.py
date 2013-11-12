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
