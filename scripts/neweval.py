#!/usr/bin/python

## tweet-norm_eval.py
##
## Last update: 2013/06/18 (Inaki San Vicente)
#
# The script returns the total accuracy of the OOV correctly treated against a reference.
# 
# Parameters: gold standard (argv[1]) filename and results filename (argv[2])
# Formats of gold standard:  \t OOVword Proposal 
#                          or
#                            \t OOVword Class Proposal 
#
#
# Formats of results file:   "\t OOVword Proposal"
#                          or
#                            \t OOVword Class Proposal 
#	when word is not variation:  "OOVword OOVword"
#                                or
#                                    "\t OOVword Class OOVword"
# Call example:
#
#        % python tweet-norm_eval.py tweet-norm-dev500_annotated.txt resultFile.txt
#
#


import sys, re

import codecs
import inspect
import os

# set PYTHONPATH
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if not curdir in sys.path:
    sys.path.append(curdir)
parentdir = os.path.split(curdir)[0]
if not os.path.join(os.path.join(parentdir, "config")) in sys.path:
    sys.path.append(os.path.join(parentdir, "config"))
if not os.path.join(os.path.join(parentdir, "data")) in sys.path:
    sys.path.append(os.path.join(parentdir, "data"))
if not os.path.join(os.path.join(parentdir, "scripts")) in sys.path:
    sys.path.append(os.path.join(parentdir, "scripts"))

# app specific imports
import tnconfig as tc
import preparation as prep

def loadFile(filename):
  resultdict=dict()
  buff=[]
  key=""
  OOVs=0
  
  for i in open(filename).readlines():
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




###############################################################
#                                                             #
#                         Main program                        #
#                                                             #
###############################################################


def main(goldStandard, resultFile):
  #global evalfh
  evalfh = open(tc.EVALFN.format(prep.find_run_id()), "w")

  # variables: 
  errors=0
  pos=0
  neg=0
  result=""
  skip=0
  # list with gold standard results
  # store the gold standard
  goldStandardDict, OOVnumber=loadFile(goldStandard)

  evalfh.write('reference loaded:  {0} tweets and {1} OOVs\n'.format(len (goldStandardDict), OOVnumber))

  gold=[]
  res=[]
  #ind=0
  key=""
  
  # store the result file
  resultDict, OOVnumberRes=loadFile(resultFile)

  evalfh.write('result file loaded:  {0} tweets and {1} OOVs\n'.format(len (resultDict), OOVnumberRes))


  # read results file line by line
  for key in resultDict.keys():
    res=resultDict[key]
    resBig=0
    goldBig=0
    #evalfh.write('id lerroa! '+line+'\n')

    if (key in goldStandardDict.keys()):
      gold=goldStandardDict[key]     
    else:
      evalfh.write("WARN_1\t"+key+" tweet not in the gold standard reference, it will be omitted\n") 
      key=""   
      
    if len(gold) < len(res):
      evalfh.write('WARN_2: it seems the reference has LESS OOVs than the results --> {0} - {1} - {2}\n'.format(len(gold),len(res), key))
      resBig=1
    elif len(gold) > len(res):
      evalfh.write('WARN_2: it seems the reference has MORE OOVs than the results --> {0} - {1} - {2}\n'.format(len(gold),len(res), key))
      goldBig=1
   
    indGold=0
    ind=0
    while ind < len(res): 
      #evalfh.write('::::: %s' % line)
      
      if len(gold) < indGold+1:
         evalfh.write('WARN_2: there is no more OOVs in the reference for this tweet {0} --> omitting the rest of the OOVs in the result\n'.format(key))
         break
      # Load the OOV of the moment for lists.
      resForm,resCorrect=getReferencePair(res[ind].strip())
      goldForm,goldCorrect=getReferencePair(gold[indGold].strip())
      
      ind+=1
      indGold+=1
      # Compare both forms
      # lines in the results' and gold standard file do not corresnpond.
      if (resForm != goldForm):
        #result+= "ALIGN ERROR\t"+goldForm+"\t"+line+"\n";
        evalfh.write("ALIGN ERROR\t"+goldForm+"\t"+res[ind-1]+" -- "+str(ind)+" "+str(indGold)+" "+str(len(res))+"\n")
        if resBig==1:
          indGold-=1
        elif goldBig==1:
          ind-=1          
        errors+=1
      # correct proposal
      elif (resCorrect == goldCorrect):
        evalfh.write("POS\t"+goldForm+"\t"+resCorrect+"\t"+goldCorrect+"\n")
        pos+=1
      # wrong proposal
      else:
        neg+=1
        evalfh.write("NEG\t"+goldForm+"\t"+resCorrect+"\t"+goldCorrect+"\n")
      
    # unknown formatted line.
    #else:
     # continue

  #acc=pos*100/(pos+neg)
  acc=pos*100.0/(OOVnumber)
  #return 'ERR: {0} \nPOS: {1} \nNEG: {2} \nACCUR: {3} \n'.format(errors, pos, neg, acc)
  evalfh.write('ERR: {0} \nPOS: {1} \nNEG: {2} \nACCUR: {3} \n'.format(errors, pos, neg, acc))
  evalfh.close()

#if __name__ == '__main__':
#    evalfh.write( main(sys.argv[1], sys.argv[2]).encode('utf-8') )
#    evalfh.close()
