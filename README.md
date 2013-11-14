tnor2: Tweet Normalization
==========================

Requires
--------
 - psutil: apt-get install python-psutil
 - SRILM and pysrilm (https://github.com/njsmith/pysrilm)

Running
-------

Preferred: from Python shell.
Options can be specified in config.py, but some of the settings in that file can be modified with command line options when calling the program (adding more as we go)

``` python

>>> import sys
>>> sys.argv = [""]
>>> execfile("/path/to/tnor2/twenor/processing.py")
```

```python
# If using command line arguments


  age: processing.py [-h] [-t] [-c COMMENT] [-b] [-x MAXDISTA] [-d DISTAW]
                     [-l LMW] [-p LMPATH] [-w LM_WINDOW]

optional arguments:
  -h, --help            show this help message and exit
  -t, --tag             tag with FreeLing
  -c COMMENT, --comment COMMENT
                        comment for run (shown in cumulog.txt)

#COMMAND_LINE OPTIONS BELOW HERE NOT FUNCTIONAL (set them in config/tnconfig.py)
  -b, --baseline        baseline run: accept all OOV
  -x MAXDISTA, --maxdista MAXDISTA
                        maximum edit distance above which candidate is
                        filtered
  -d DISTAW, --distaw DISTAW
                        weight for edit-distance scores
  -l LMW, --lmw LMW     weight for language model scores
  -p LMPATH, --lmpath LMPATH
                        path to Arpa file for language model
  -w LM_WINDOW, --lm_window LM_WINDOW
                        left-window for context lookup in language model

E.g.

>>> sys.argv = ["", "--comment", "test Freeling tagging", "--tag"]
>>> execfile("/path/to/tnor2/twenor/processing.py")
```



Also from command line:

``` python

python /path/to/tnor2/twenor/processing.py

```

Structure
-------

```
tnor2
 |_ config
    |_ tnconfig.py              Config file
 |_ scripts
    |_ neweval.py               Tweet-Norm workshop's evaluation script
 |_ twenor
    |_ preparation.py           Common preparation functions
    |_ freelmgr.py              Freeling Analyzer calls
    |_ twittero.py              Basic tweet analysis objects: Tweet, Token, OOV, ...
    |_ preprocessing.py         OOV preprocessing with regexes and lists
    |_ editor.py                Candidate Generation and Distance-Scoring
    |_ lmmgr.py                 Language Model creation, candidate lookup and scoring
    |_ postprocessing.py        Recasing
    |_ entities.py              Form lookup in entity resources
    |_ processing.py            Main program
 |_ data                        Regex lists, entity lists, correction model data, LMs etc.
 |_ evaluation
    |_ dev                      devset texts and annotations
    |_ eval                     test-set texts and annotations
```

