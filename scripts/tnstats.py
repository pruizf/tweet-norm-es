#!/usr/bin/python

## Based on tweet-norm_eval.py by Inaki San Vicente from Tweet-Norm 

import codecs
import sys, re
import editor
import twittero
from twittero import OOV

# Aux functions --------------------------------------------
def loadFile(filename):
  resultdict=dict()
  buff=[]
  key=""
  OOVs=0
  for i in codecs.open(filename, "r", "utf8").readlines():
    if re.match (r'(\d{4,})',i):
      if (key != ""):
        resultdict[key]=[]
        resultdict[key]=buff
        buff=[]
      key=i.strip()
    else:
      buff.append(i.strip())
      OOVs+=1
  # insert the last element
  if (key != ""):
    resultdict[key]=[]
    resultdict[key]=buff
    buff=[] 
  return (resultdict, OOVs)


def getReferencePair(line):
  goldFields=re.split('\s+',line)
  form=goldFields[0]
  correct=goldFields[1]
  #this is to accept original annotated corpora.
  if len(goldFields) > 2:
    correct=goldFields[2]      
  # if correct form is '-' means there is no changes, and thus the correct form is the original form
  if (correct == '-'):
    correct=form    
  return (form,correct)

def hash_gold_standard(goldStandard):
  # list with gold standard results
  goldStandardDict, OOVnumber=loadFile(goldStandard)
  print "= Coverage Stats"
  print 'reference loaded: {0} tweets and {1} OOVs\n'.format(len (goldStandardDict), OOVnumber)
  key=""
  outDict = {}
  for key in goldStandardDict:
    outDict[key] = []
    if goldStandardDict[key] == []:
      continue
    else:
      goldForm,goldCorrect=getReferencePair(goldStandardDict[key][0].strip())
      #print goldForm, goldCorrect
      outDict[key].append((goldForm, goldCorrect))
  return outDict

# Stats functions ------------------------------------------
def get_upper_bound(refe, resu):
  """ refe : tid (oov, corr)
      resu : [Tweet1 , ..... TweetN]"""
  our_resus = {}
  coverage = {}
  for tid in refe:
    our_resus[tid] = {}
    coverage[tid] = {}
    # add to baseline
    if refe[tid] == []:
      coverage[tid] = {}
      continue
    # get our candidates
    tweet = [t for t in resu if t.tid == tid][0]
    resu_oovs = [tok for tok in tweet.toks if isinstance(tok, OOV)]
    for rso in resu_oovs:
      our_resus[tid][rso.form] = []
      cands = []
      if rso.cands_filtered is not None:
        cands.extend([cand.form for cand in rso.cands_filtered])
      cands.append(rso.safecorr)
      cands.append(rso.abbrev)
      cands.append(rso.runin)
      cands.append(rso.ppro_recorr)
      cands.append(rso.edbase)
      if rso.best_ed_cando is not None:
          cands.append(rso.best_ed_cando.form)
      cands.append(rso.befent)
      cands.append(rso.aftent)
      cands.append("".join((rso.aftent[0].upper(), rso.aftent[1:])))
      our_resus[tid][rso.form] = list(set(cands))
    for rfo in refe[tid]:
      if rfo[0] in our_resus[tid]:
        if rfo[1] in our_resus[tid][rfo[0]]:
          if rfo[1] == rfo[0]:
            coverage[tid][rfo[1]] = "baseline"
          else:
            coverage[tid][rfo[1]] = "covered"
        else:
          coverage[tid][rfo[1]] = "missing"
  # Stats
  baselines, covered, missing, no_oov = 0, 0, 0, 0
  for tid in coverage:
    if len(coverage[tid]) == 0:
      no_oov += 1
      continue
    for key in coverage[tid]:
      if coverage[tid][key] == "baseline":
        baselines += 1
      elif coverage[tid][key] == "covered":
        covered += 1
      elif coverage[tid][key] == "missing":
        missing += 1
  stats = {"baselines": baselines, "covered": covered,
           "missing": missing, "no_oov": no_oov}
  total_tweets = baselines + covered + missing + no_oov
  print "Baseline OOV", baselines
  print "Covered OOVs", covered
  print "Missing OOVs", missing
  print "NO OOV Tweets", no_oov
  print "Total Tweets", total_tweets
  upper_bound = (float(baselines + covered) / (baselines + covered + missing), 
                 float(covered) / (covered + missing))
  stats["total_tweets"] = total_tweets
  stats["upper_bound"] = upper_bound
  print "UpperBoundOOV: {0}%".format(upper_bound)
  return coverage, stats
