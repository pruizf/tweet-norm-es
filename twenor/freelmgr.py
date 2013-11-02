import codecs
import os
import logging
import psutil
import sys
import tnconfig as tc #assumes PYTHONPATH set in module importing this one

# logging
logging.basicConfig(level=tc.loglevel)
lgr = logging.getLogger(__name__)
#lfh = logging.FileHandler(os.path.join(tc.LOGDIR, "%s.log" % __name__))
lfh = logging.FileHandler(os.path.join(tc.LOGDIR, "run_%s.log" % tc.RUNID))
frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lfh.setFormatter(frmt)
lgr.propagate = False
lgr.addHandler(lfh)


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
    for tid in txtdico:
        lgr.info("Tagging %s" % tid)
        temp = codecs.open(tempfn, "w", "utf8")
        temp.write(txtdico[tid])
        temp.close()
        outfn = os.path.join(tc.TAGSDIR, "%s.tags" % tid)
        # tag
        run_fl_client(tempfn, outfn)
    os.remove(tempfn)
