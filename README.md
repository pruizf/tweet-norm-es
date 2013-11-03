tnor2: Tweet Normalization
==========================

Requires
--------
 - psutil: apt-get install python-psutil
 - BeautifulSoup: pip  or easy_install beautifulsoup4, apt-get install python-bs4


Structure
-------
The structure of the program is

tnor2
 |_ config
    |_ tnconfig.py		Config file
 |_ scripts
    |_ neweval.py		Tweet-Norm workshop's evaluation script
 |_ twenor
    |_ preparation.py		Common preparation functions
    |_ freelmgr.py		Freeling Analyzer calls
    |_ twittero.py		Basic tweet analysis objects: Tweet, Token, OOV, ...
    |_ processing.py		Main Program
    #TODO: spell-checking modules themselves
  |_ data			Regex lists, entity lists, correction model data, LMs etc.
  |_ evaluation
    |_ dev			devset texts and annotations
    |_ eval			test-set texts and annotations

Running
-------

``` python

python /path/to/tnor2/twenor/processing.py

```

Or from Python shell

``` python

>>> import sys
>>> sys.argv = [""]
>>> execfile("/path/to/tnor2/twenor/processing.py")
```


