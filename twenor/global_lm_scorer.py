# -*- coding: utf-8 -*-

import os, network, twittero, pdb, kenlm, processing, postprocessing, preparation, pprint, unicodedata

from network import Network, TweetCandProc

from twittero import OOV

from processing import write_out

LM_PATH = "/home/VICOMTECH/share/SUMAT/LanguageModels/TweetNorm/opensubs+tweets.tok.tc.es.blm"

final_punc = [".", "!", "?"]

cap_context = [".", "!", "?", '"', "...", "(", ")", "/"]

def get_reduced_cands(tok, tweet, cand_list):
    orig_and_cands = [(tok.form, c.form, set_recase_val(tok, tweet), True) for c in cand_list]
    if len(orig_and_cands) > 1:
        orig_and_cands = orig_and_cands[:1]                        
    return orig_and_cands

def is_capitalization_context(tok_pos, tweet):
    return tok_pos == 0 \
            or ( ((tok_pos - 1) > 0) \
                and ( (tweet.toks[tok_pos-1].form in cap_context))) 
                       #or (tok_pos == 1 and (tweet.toks[0].form[0] == "@")))) 

def is_accented_variant(acc_str, str2):
    return unicodedata.normalize('NFD', acc_str).encode('ASCII', 'ignore') \
                == str2.encode('ASCII', 'ignore')


#--                  
def set_recase_val(tok, tweet):    
    return tok.form[0].isupper() and len(tok.form) > 1 and is_capitalization_context(tok.posi, tweet)                      
            
                
def get_candidate_combinations(tweets):    
    print "---------------- Computing candidate combinations ----------------"
    res = []
    nw = Network()    
    tcp = TweetCandProc()
    orig_and_cands = []
    tweet_sqs = []
    for tweet in tweets:
        print("Candidate sequence extraction for tweet #{0}").format(tweet.tid)
        nw.initialize()
        tcp.initialize(tweet.tid)
        del tweet_sqs[:]
        for tok in tweet.toks:             
            if tok.form == u"XD":
                pdb.set_trace()        
            #-- Check trusted corrections first and set them as unique candidate if they exist           
            del orig_and_cands[:]   
            if isinstance(tok, OOV):
                if tok.safecorr != None:                    
                    orig_and_cands.append((tok.form, tok.safecorr, set_recase_val(tok, tweet), True))
                elif tok.abbrev != None:
                    orig_and_cands.append((tok.form, tok.abbrev, set_recase_val(tok, tweet), True))
                elif tok.runin != None:
                    orig_and_cands.append((tok.form, tok.runin, set_recase_val(tok, tweet), True))    
                else:
                    if tok.entcand != None:
                        orig_and_cands.append((tok.form, tok.entcand, set_recase_val(tok, tweet), True))                    
                        if tok.ed_filtered_ranked != None:
                            rcands = get_reduced_cands(tok, tweet, tok.ed_filtered_ranked)
                            orig_and_cands.extend([tpl for tpl in rcands \
                                if (is_accented_variant(tpl[1], tok.entcand) \
                                    or (is_accented_variant(tpl[1], tpl[0])))])

                    if tok.ppro_recorr != None:
                        if tok.ed_filtered_ranked != None:
                            rcands = get_reduced_cands(tok, tweet, tok.ed_filtered_ranked)
                            if tok.ppro_recorr_IV:
                                orig_and_cands.append((tok.form, tok.ppro_recorr, set_recase_val(tok, tweet), True))      
                                orig_and_cands.extend([tpl for tpl in rcands \
                                    if (is_accented_variant(tpl[1], tok.ppro_recorr) \
                                        or (is_accented_variant(tpl[1], tpl[0])))])
                            elif tok.entcand == None:
                                orig_and_cands.extend(rcands)
                                                
                if len(orig_and_cands) == 0 and tok.ed_filtered_ranked != None:
                    orig_and_cands = get_reduced_cands(tok, tweet, tok.ed_filtered_ranked)                    

            if len(orig_and_cands) == 0:
                orig_and_cands.append((tok.form, tok.form, set_recase_val(tok, tweet), isinstance(tok, OOV)))
               
            nw.add_leaves(orig_and_cands)           
                     
        print("Candidates network: {0} nodes - {1} paths - depth: {2}").format(nw.get_num_nodes(), nw.get_num_paths(), nw.get_depth())            
        nw.close()   
        nw.traverse(tcp)

        all_combs = nw.get_results()

        for comb in all_combs:            
            tweet_sqs.append((tweet.tid, comb))       
        res.append(tweet_sqs[:])

    print "Done."            
    return res
    
def get_kenlLM_scores(tweet_sqs_list):
    print "---------------- Scoring with KenLM ----------------"
    res = []    
    model = kenlm.LanguageModel(LM_PATH)
    tid_results = []
    for tsq in tweet_sqs_list:
        del tid_results[:]  
        i = 0
        for csq in tsq: 
            i += 1
            print("KenLM scoring: sequence {0} from tweet #{1}").format(i, csq[0])        
            tok_sq = [tpl[1] for tpl in csq[1]]
            orig_and_cands_sq = [oc for oc in csq[1]]
            tid_results.append((csq[0], orig_and_cands_sq, model.score(' '.join(tok_sq)))) 
        res.append(tid_results[:])
    print "Done."
    return res
    
def get_best_candidate_sequence(sq):
    sq.sort(key=lambda tpl: tpl[2])
    if len(sq) > 0:        
        return sq[-1]
    else:
        return None
    
def report_results(list_best):
    print "---------------- Reporting results ----------------"
    res = {}
    for b in list_best:
        tpls = [c for c in b[1]]
        for tpl in tpls:
            if tpl[3]: #-- i.e. is OOV word
                if not res.has_key(b[0]):
                    res[b[0]] = []            
                if tpl[2] == True: #-- i.e. the word was truecased                 
                    res[b[0]].append((tpl[0], tpl[1][0].upper() + tpl[1][1:])) 
                else:
                    res[b[0]].append((tpl[0], tpl[1]))
    write_out(res)
    print "Done."
    
def run(tweets):
    all_cands = get_candidate_combinations(tweets)
    all_sq_tpls = get_kenlLM_scores(all_cands)
    list_best = []
    print "---------------- Selecting best sequences ----------------"
    for sqtpl in all_sq_tpls:
        best = get_best_candidate_sequence(sqtpl)
        list_best.append(best) 
    print "Done."

    report_results(list_best)


