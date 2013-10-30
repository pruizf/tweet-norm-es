import codecs
from collections import defaultdict
import inspect
import re
import tnconfig as tc #assumes PYTHONPATH properly set in module importing this module


def find_id_order(orderfile=tc.id_order):
    id_order = []
    for line in open(orderfile).readlines():
        id_order.append(line.rstrip())
    return id_order

def find_ref_OOVs(ref_set):
    """Find the OOVs given in golden set, for each tweet. This is
       useful since tokenization is not always exactly the same in
       our FreeLing output and in the ref set. And also the ref set
       has some mistakes, tokens that should not be OOVs are, and viceversa."""
    ref_OOVs = defaultdict(list)
    with codecs.open(ref_set, "r", "utf8") as ref:
        id_matcher = re.compile(r"^[0-9]+$")
        line = ref.readline()
        while line:
            if re.match(r"^\s+$", line):
                line = ref.readline()
                continue
            if re.match(id_matcher, line.strip()):
                tid = line.strip()
                ref_OOVs[tid]
                #print "Matched %s" % tid
            else:
                if tc.EVAL:
                    ref_OOVs[tid].append(line.split("\t")[1].rstrip())
                    #print "Added %s" % line.split("\t")[1].split(" ")[0]
                else:
                    ref_OOVs[tid].append(line.split("\t")[1].split(" ")[0])
            line = ref.readline()
        return dict(ref_OOVs)

def grab_texts(txtfn):
    txtdic = {}
    with codecs.open(txtfn, "r", "utf8") as texts:
        for line in texts:
            lines = line.rstrip().split("\t")
            txtdic[lines[0]] = lines[-1]
    return txtdic
    

    
    
 
