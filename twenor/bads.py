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
