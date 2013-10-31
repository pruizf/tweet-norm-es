#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import inspect
import logging
import os
import pprint
import re
import shutil
import subprocess
import sys
import time

# set PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
if not curdir in sys.path:
    sys.path.append(curdir)
parentdir = os.path.split(curdir)[0]
if not os.path.join(os.path.join(parentdir, "config")) in sys.path:
    sys.path.append(os.path.join(parentdir, "config"))
if not os.path.join(os.path.join(parentdir, "data")) in sys.path:
    sys.path.append(os.path.join(parentdir, "data"))
 
# app-specific imports
import tnconfig as tc
import preparation as prep
import freelmgr as fl
from twittero import Tweet, Token


# processing
id_order = prep.find_id_order()
ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
textdico = prep.grab_texts(tc.TEXTS)
# now need to Freeling-tag these texts
# start Freeling server if not running
if not fl.check_server(tc.fl_port):
    fl.start_server()
# tag texts with Freeling
if tc.TAG:
    fl.tag_texts(texts)

# read text and token tags into Tweet and Token objects
all_tweeto = {}
# create Tweet objects
for tid in textdico:
    if "%s.tags" % tid not in os.listdir(tc.TAGSDIR):
        print "Missing tags for %s" % tid
    all_tweeto[tid] = Tweet(tid, textdico[tid])
    all_tweeto[tid].find_OOV_status(ref_OOVs)

for tid in all_tweeto:
    if all_tweeto[tid].hasOOVs:
        all_tweeto[tid].set_ref_OOVs(ref_OOVs[tid])



