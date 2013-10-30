import freeling as fl
import sys
sys.path.append("/home/pruiz/DATA/projects/Tweet-Norm/twenor2/config")
import tnconfig as tc

''' As per API sample.py '''

FREELINGDIR = "/usr/local"
DATA = FREELINGDIR + "/share/freeling/"
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
#twk = fl.tokenizer(tc.USERTOK)
twk = fl.tokenizer(DATA + LANG + "/tokenizer.dat")
#mf = fl.maco(op)

