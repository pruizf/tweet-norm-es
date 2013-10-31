import freeling as fl
import sys
sys.path.append("/home/pruiz/DATA/projects/Tweet-Norm/twenor2/config")
import tnconfig as tc


def run_fl_client(fn, outfn):
    """ Run a FreeLing client on a server configured as in the devset
        configuration for task"""
    lgr.info("Orig call")
    port = orig_server[1].replace("-p ", "")
    comstr = "sudo %s %s <%s >%s" % (anacli, port, fn, outfn)
    lgr.info(comstr)
    os.system(comstr)



''' As per API sample.py '''

FREELINGDIR = "/usr/local"
DATA = FREELINGDIR + "/share/freeling"
LANG = 'es'

# set maco analyzer options

op = fl.maco_options("es")

# 11 bool for set_active_modules()
""" /usr/local/share/freeling/config/es.cfg
 59 AffixAnalysis=yes
 60 MultiwordsDetection=yes
 61 NumbersDetection=yes
 62 PunctuationDetection=yes
 63 DatesDetection=yes
 64 QuantitiesDetection=yes
 65 DictionarySearch=yes
 66 ProbabilityAssignment=yes
 67 OrthographicCorrection=no
 68 DecimalPoint=,
 69 ThousandPoint=.
"""

op.set_active_modules(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
op.set_data_files("",
                  DATA + LANG + "/locucions.dat",
                  DATA + LANG + "/quantities.dat",
                  DATA + LANG + "/afixos.dat",
                  DATA + LANG + "/probabilitats.dat",
                  DATA + LANG + "/dicc.src",
                  DATA + LANG + "/np.dat",
                  DATA + "/common/punct.dat",
                  DATA + LANG + "/corrector/corrector.dat")

# compatibility with task results
op.set_retok_contractions(0)
op.UserMap = True
op.UserMapFile = tc.USERMAP

# tweet tokenizer from workshop
twk = fl.tokenizer(tc.USERTOK)
#mf = fl.maco(op)

