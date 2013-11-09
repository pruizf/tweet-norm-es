import cherrypy
import kenlm
from cherrypy import expose

lmp = "/home/ps/DATA/wk/VT/projects/Tweet-Norm/SUMATCasedLM_kenlm_es.arpa"

#klm = kenlm.LanguageModel(lmp)
DATADIR = "/home/ps/DATA/wk/VT/projects/Tweet-Norm"

class LMMgr:
    klm = None

    @expose
    def create(self):
        print "Creating model"
        klm = kenlm.LanguageModel(lmp)
        self.klm = klm
        print "Done"

    @expose
    def find_score(self, sente):
        sco = self.klm.score(sente)
        return "%s" % sco

print "Starting Engine"
cherrypy.quickstart(LMMgr())
print "Done"
