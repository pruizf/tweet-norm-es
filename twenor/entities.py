import inspect
import logging
import os
import sys

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
import preparation as prep
import tnconfig as tc
import editor

# logging
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id())
lgr, lfh = prep.set_log(__name__, logfile_name)

class EntityMgr:
    def __init__(self, ent_hash, ivs, edimgr, lmmgr):
        self.ent_hash = ent_hash
        self.ivs = ivs
        self.edimgr = edimgr
        self.lmmgr = lmmgr

    def find_entity(self, token, toktype="n/a"):
        """Check a token and (if needed) several case-variants in an entity-hash"""
        if token in self.ent_hash:
            lgr.debug("EN [%s] [%s] found [as_is] in ent_hash" % (toktype, token))
            return {"corr": token, "applied": True}
        else:
            if not token.isupper():
                inicap = "".join([token[0].upper(), token[1:]])
                if inicap in self.ent_hash:
                    lgr.debug("EN [%s] [%s], from [%s] found [inicapped] in ent_hash" % (toktype, inicap, token))
                    return {"corr": inicap, "applied": True}
                allcaps = token.upper()
                if allcaps in self.ent_hash:
                    lgr.debug("EN [%s] [%s], from [%s] found [allcapsed] in ent_hash" % (toktype, allcaps, token))
                    return {"corr": allcaps, "applied": True}
                else:
                    return {"corr": token, "applied": False}
            elif token.isupper():
                allcaps2inicap = "".join([token[0], token[1:].lower()])
                if allcaps2inicap in self.ent_hash:
                    lgr.debug("EN [%s] [%s], from [%s| found [all2inicapsed] in ent_hash" % (toktype, allcaps2inicap, token))
                    return {"corr": allcaps2inicap, "applied": True}
                else:
                    return {"corr": token, "applied": False}
   
    def add_entity_candidates(self, form):
        """<form> is the string to generate edits for"""
        entcands_string = self.edimgr.generate_candidates(form) #returns a set
        entcands_string_upper = ["".join((c[0].upper(), c[1:])) for c in
                                 entcands_string]
        entcands_string.extend(entcands_string_upper)
        entcands_obj = []
        if len(entcands_string) > 0:
            for ecand in entcands_string:
                entcands_obj.append(editor.Candidate(ecand))
            for ecando in entcands_obj:
                ecando.set_dista(self.edimgr.levdist(ecando.form, form))
        entcands_filtered = [cand for cand in entcands_obj if cand.dista >= -0.5]
        entcands_final = []
        for cand in entcands_filtered:
            is_ent = self.find_entity(cand.form)
            if is_ent["applied"]:
                entcands_final.append(cand)
        return entcands_final

