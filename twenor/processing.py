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

# processing
id_order = prep.find_id_order()
ref_OOVs = prep.find_ref_OOVs(tc.ANNOTS)
texts = prep.grab_texts(tc.TEXTS)
# now need to freeling tag these texts


