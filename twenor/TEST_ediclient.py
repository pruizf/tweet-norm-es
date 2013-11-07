# ediclient

import codecs
import inspect
import logging
import os
import sys

# PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if not curdir in sys.path:
    sys.path.append(curdir)
parentdir = os.path.split(curdir)[0]
if not os.path.join(os.path.join(parentdir, "config")) in sys.path:
    sys.path.append(os.path.join(parentdir, "config"))
if not os.path.join(os.path.join(parentdir, "data")) in sys.path:
    sys.path.append(os.path.join(parentdir, "data"))

import tnconfig as tc
import edcosts

if "tc" in dir(sys.modules["__main__"]): reload(tc)
if "edi2" in dir(sys.modules["__main__"]): reload(edi2)

import editor as edi2
reload(edi2.tc)

edisco = edi2.EdScores(edcosts)
edisco.read_cost_matrix()
edisco.find_matrix_stats()
exm = edisco.create_matrix_hash()
myeditor = edi2.Editor(exm, tc.IVDICO)
myeditor.prep_alphabet()
myeditor.generate_and_set_known_words()

