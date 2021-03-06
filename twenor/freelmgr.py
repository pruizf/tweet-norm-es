import codecs
import inspect
import os
import logging
import psutil
import sys
import time

import preparation as prep
import tnconfig as tc

# logging
logfile_name = os.path.join(tc.LOGDIR, "run_%s.log" % prep.find_run_id(increase=True))
lgr, lfh = prep.set_log(__name__, logfile_name, False)


def check_server(port):
    """Check if Freeling server is running on port"""
    listening = False
    flprocs = [p for p in psutil.get_process_list()
               if p.name.startswith("analyze")]
    for flp in flprocs:
        flpcons = flp.get_connections()
        if len(flpcons) > 0 and flpcons[0].local_address[1] == port:
            listening = True
            break
    if listening:
        return True
    return False

def start_server(servtype="default"):
    global comstr #debug
    if servtype == "default":
        tc.fl_server.extend(tc.fl_options)
        comstr = " ".join(tc.fl_server)
    lgr.info("Starting server %s" % servtype)
    os.system("%s %s&" % (tc.ANA, comstr))

def run_fl_client(inp, outfn):
    """Run a FreeLing client on a server configured as in the devset
       configuration for task"""
    port = tc.fl_server[1].replace("-p ", "")
    if os.path.isfile(inp):
        comstr = "%s %s <%s >%s" % (tc.ANACLI, port, inp, outfn)
        lgr.debug(comstr)
    os.system(comstr)

def tag_texts(txtdico):
    """Takes hash of texts by ID. Tags with Freeling and writes to output
       files named after the ID"""
    if not os.path.exists(tc.TAGSDIR):
        os.makedirs(tc.TAGSDIR)
    tempfn = os.path.join(tc.TAGSDIR, "temp")
    tnbr = 0
    for tid in txtdico:
        lgr.info("Tagging %s" % tid)
        temp = codecs.open(tempfn, "w", "utf8")
        temp.write(txtdico[tid])
        temp.close()
        outfn = os.path.join(tc.TAGSDIR, "%s.tags" % tid)
        # tag
        run_fl_client(tempfn, outfn)
        tnbr += 1
        if tnbr % 100 == 0:
            print "Tagged {}".format(time.asctime(time.localtime()))
    os.remove(tempfn)
