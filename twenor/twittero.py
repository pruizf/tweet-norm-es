""" Basic Twitter Objects """
 
class Tweet:
    def __init__(self, tid, itext):
        self.tid = tid
        self.itext = itext
    hasOOVs = None
    
    def find_OOVs(self):
        pass
    def find_tokens(self):
        pass
    def set_ref_OOVs(self, ref_OOVs):
        self.ref_OOVs = ref_OOVs
    def find_OOV_status(self, ref_OOVs):
        if self.tid not in ref_OOVs:
            self.hasOOVs = False
        else:
            self.hasOOVs = True


class Token:
    def __init__(self, form):
        self.form = form
    def find_lemma(self):
        pass
    def find_posi(self):
        pass
    def isOOV(self):
        pass
