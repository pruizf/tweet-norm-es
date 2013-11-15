# Import module to test results of processing.add_more_entities()

import twittero

def test(all_tweets):
    for t in all_tweets:
        for tok in t.toks:
            if tok.isOOV:
                if tok.form in t.ref_OOVs:
                    if len(tok.entcands) > 0:
                        for bla in tok.entcands:
                            print t.tid, "F", repr(tok.form), "EC", repr(bla)
