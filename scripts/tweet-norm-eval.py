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

import sys, re

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




###############################################################
#                                                             #
#                         Main program                        #
#                                                             #
###############################################################


def main(goldStandard, resultFile):

  # variables: 
  errors=0
  pos=0
  neg=0
  result=""
  # list with gold standard results
  # store the gold standard
  goldStandardDict, OOVnumber=loadFile(goldStandard)

  sys.stderr.write('reference loaded:  {0} tweets and {1} OOVs\n '.format(len (goldStandardDict), OOVnumber))

  gold=[]
  ind=0
  key=""
  # read results file line by line
  for line in open(resultFile).readlines():
    # if line starts with number it is a tweet id
    if re.match (r'(\d{4,})',line):
      ind=0
      key=line.strip()
      #sys.stderr.write('id lerroa! '+line+'\n')
      if (not goldStandardDict[key]):
        result+= "ERROR\t"+line+" tweet not in the gold standard reference\n"; 
      else:
        gold=goldStandardDict[key]        
      
    # line contains an OOV word.
    else: #re.match (r'\t', line):
      if key == "":
        sys.stderr.write('error: no tweet id line omitted %s \n' % line) 
        continue
      #sys.stderr.write('oov lerroa! %s \n' % '::'.join(gold))  
      #sys.stderr.write('oov lerroa! '+line+'\n')      
      line=line.strip()
      resultsFields=re.split('\s+', line)
       
      # this is to accept both "form correctform" and "form class correct" formats
      if len(resultsFields) > 2:
        resultsFields[1]=resultsFields[2]

      # this condition allows result file to have the format "form -" when the form is correct 
      if resultsFields[1] == '-':
         resultsFields[1]=resultsFields[0]

      goldFields=re.split('\s+',gold[ind].strip())
      ind+=1
      goldForm=goldFields[0]
      goldCorrect=goldFields[1]
      #this is to accept original annotated corpora.
      if len(goldFields) > 2:
        goldCorrect=goldFields[2]
      
      # if correct form is '-' means there is no changes, and thus the correct form is the original form
      if (goldCorrect == '-'):
        goldCorrect=goldForm
        


      # Compare both forms
      # lines in the results' and gold standard file do not corresnpond.
      if (resultsFields[0] != goldForm):
        result+= "ALIGN ERROR\t"+goldForm+"\t"+line+"\n";
        sys.stderr.write("ALIGN ERROR\t"+goldForm+"\t"+line+"\n")
        errors+=1
      # correct proposal
      elif (resultsFields[1] == goldCorrect):
        #print "POS\t"+goldForm+"\t"+resultsFields[1]+"\t"+goldCorrect
        pos+=1
      # wrong proposal
      else:
        neg+=1
        print "NEG\t"+goldForm+"\t"+resultsFields[1]+"\t"+goldCorrect   
      
    # unknown formatted line.
    #else:
     # continue

  #acc=pos*100/(pos+neg)
  acc=pos*100.0/(OOVnumber)
  return 'ERR: {0} \nPOS: {1} \nNEG: {2} \nACCUR: {3} '.format(errors, pos, neg, acc)

#main(goldStandard, resultFile)
if __name__ == '__main__':
    print main(sys.argv[1], sys.argv[2]).encode('utf-8')
