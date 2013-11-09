import string

def main(all_tweets, mytid):
    t = [t for t in all_tweets if t.tid == mytid][0]

    for x in t.found_OOVs:
        #print x.form, len(x.cands), x.has_LM_cands
        for c in x.cands:
            if c.dista >= -1.5:
                if type(c.dista) is str or type(c.dista) is int:
                    c.dista = float(c.dista)
                try:
                    #print x.form, c.form, c.dista, c.lmsco, c.dista + 1.0/c.lmsco
                    print "{}\t{}\t{}\t{}\t{}".format(string.ljust(x.form.encode("utf8"), 10),
                                                    string.ljust(c.form.encode("utf8"), 10),
                                                    string.zfill(c.dista, 3),
                                                    string.zfill(c.lmsco, 15),
                                                    string.zfill(c.dista + 1.0/c.lmsco, 15))
                except TypeError:
                    print "{}\t{}\t{}\t{}\t".format(string.ljust(x.form.encode("utf8"), 10),
                                                    string.ljust(c.form.encode("utf8"), 10),
                                                    string.zfill(c.dista, 3),
                                                    string.zfill(c.lmsco, 15),
                                                    string.zfill(c.dista, 3))
                    
