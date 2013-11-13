import codecs
from collections import defaultdict
import inspect
import logging
import os
import re
import subprocess
import tnconfig as tc #assumes PYTHONPATH properly set in module importing this module

def set_log(lh_name, lf_name, propa=False):
    """Set Logger based on log handler and logging.FileHandler name.
       Return the Logger instance and FileHandler instance for access
       from importing module."""
    logging.basicConfig(level=tc.loglevel)
    lgr = logging.getLogger(lh_name)
    lfh = logging.FileHandler(lf_name)
    frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    lfh.setFormatter(frmt)
    lgr.propagate = propa
    lgr.addHandler(lfh)
    return (lgr, lfh)

def find_git_revnum():
    """Find Git revision number for revision used"""
    git_dir = "{0}/.git".format(tc.APPDIR)    
    return subprocess.check_output(["git", "--git-dir=%s" % git_dir, "describe", "--always"]).strip()
    
def find_run_id(increase=False):
    """Run ID for all modules. Should move to a singleton somewhere"""
    if tc.RUNID is None:
        if not os.path.exists(tc.RUNID_FILE):
            with open(tc.RUNID_FILE, "w") as new_runid_file:
                new_runid_file.write("1")
        tc.RUNID = open(tc.RUNID_FILE, "r").read().rstrip()
        with open(tc.RUNID_FILE, "w") as new_runid_file:
            new_runid_file.write(str(int(tc.RUNID) + 1))
            tc.RUNID = str(int(tc.RUNID) + 1)
    elif increase:
        tc.RUNID = int(tc.RUNID) + 1
        with open(tc.RUNID_FILE, "w") as new_runid_file: 
            new_runid_file.write(str(int(tc.RUNID)))
    return tc.RUNID

def find_id_order(orderfile=tc.id_order):
    """ID Order to write out results as in reference"""
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
                ref_OOVs[tid].append(line.split("\t")[1].split(" ")[0])
            line = ref.readline()
        return dict(ref_OOVs)

def grab_texts(txtfn):
    txtdic = {}
    with codecs.open(txtfn, "r", "utf8") as texts:
        for line in texts:
            lines = line.rstrip().split("\t")
            if lines[-1] != "Not Available":
                txtdic[lines[0]] = lines[-1]
            else:
                txtdic[lines[0]] = ""
    return txtdic


    

    
    
 
