from nltk.tokenize import sent_tokenize
import re

def isMergeTag(textData):
    mergeTagPatt = r"\{(.*?)\}"
    allTag = ['{'+ i+ '}' for i in re.findall(mergeTagPatt, textData)]
    if len(allTag)>0:
        return True
    else:
        return False

    
sentence = 'God is Great! I won a lottery. These tokenizers work by separating the {words} using punctuation and {spaces}. And as mentioned in the code outputs above, it does not discard the punctuation, allowing a user to decide what to do with the punctuations at the time of pre-processing. Another sent mtag.'
sentTok = sent_tokenize(sentence)
isMTag = [isMergeTag(ii) for ii in sentTok]
finalSent = []
prv = isMTag[0]
tmpd = [sentTok[0]]
for ii in range(1,len(isMTag)):
    if isMTag[ii] == prv:
        tmpd.append(sentTok[ii])
    else:
        finalSent.append({'sent': ' '.join(tmpd),'isTag': prv})
        tmpd=[sentTok[ii]]
    prv = isMTag[ii]
finalSent.append({'sent': ' '.join(tmpd),'isTag': prv})

for ii in finalSent:
    ## generate sentence and grab durations
    ii['durations'] = 0
print(finalSent)
