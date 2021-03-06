tweet-norm-es: Spanish Tweet Normalization
===============================================
Our system for the [Tweet-Norm 2013](http://komunitatea.elhuyar.eus/tweet-norm/) competition, which we later improved for the paper in [Ruiz, Cuadros, Etchegoyhen (2014)](http://journal.sepln.org/sepln/ojs/ojs/index.php/pln/article/download/4902/2916). (See complete references at the end).

Requires
--------
 - psutil: apt-get install python-psutil
 - SRILM and pysrilm (https://github.com/njsmith/pysrilm)
 - KenLM (https://github.com/kpu/kenlm)

Running
-------

Preferred: from Python shell.
Options can be specified in tnconfig.py, but some of the settings in that file can be modified with command line options when calling the program (we'll expose more options in the CLI in the future).

``` python
>>> import sys
>>> sys.argv = [""]
>>> execfile("/path/to/tweet-norm-es/twenor/processing.py")
```

    
    # If using command line arguments instead of tnconfig.py


    Usage: processing.py [-h] [-t] [-c COMMENT]

    optional arguments:
      -h, --help            show this help message and exit
      -t, --tag             tag with FreeLing
      -c COMMENT, --comment COMMENT
                            comment for run (shown in cumulog.txt)

    #COMMAND_LINE OPTIONS BELOW HERE NOT YET FUNCTIONAL (set them in config/tnconfig.py)
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

```python
>>> sys.argv = ["", "--comment", "test Freeling tagging", "--tag"]
>>> execfile("/path/to/tnor2/twenor/processing.py")
```



Also from command line:

``` python

python /path/to/tweet-norm-es/twenor/processing.py

```

Project Structure
-----------------

```
tweet-norm-es
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
    |_ network.py               Combination network to generate all candidate combinations for a tweet
    |_ global_lm_scorer.py      Applies candidate-combination network
 |_ data                        Regex lists, entity lists, correction model data, LMs etc.
 |_ evaluation
    |_ dev                      devset texts and annotations
    |_ eval                     test-set texts and annotations
```

System Architecture
-------------------

![System Architecture](./misc/tweet-norm-system-arch.png)


Publications
------------

- Ruiz Fabo, Pablo, Montse Cuadros, and Thierry Etchegoyhen. (2014). [Lexical Normalization of Spanish Tweets with Rule-Based Components and Language Models.](http://journal.sepln.org/sepln/ojs/ojs/index.php/pln/article/download/4902/2916) _Procesamiento del Lenguaje Natural 52_:45-52. SEPLN, Spanish NLP Society. 

- Ruiz, Pablo, Montse Cuadros, and Thierry Etchegoyhen. (2013) [Lexical Normalization of Spanish Tweets with Preprocessing Rules, Domain-specific Edit Distances, and Language Models.](http://ceur-ws.org/Vol-1086/paper12.pdf) In _Tweet-Norm@ SEPLN_, pp. 59-63. IV Congreso Español de Informática.

