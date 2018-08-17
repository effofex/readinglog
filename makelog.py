from jinja2 import Template  # Mapping post info into a readinglog
import os.path               # File manipulation

#TODO thumbnail size
#TODO clickable images

import urllib.request
import gzip
import requests
from sys import argv
from bs4 import BeautifulSoup
import re
import time

# Truncate a blob of text at a word boundary near the length limit
def smart_truncate(content, length=100, suffix='…'):
    #adapted from https://stackoverflow.com/questions/250357/truncate-a-string-without-ending-in-the-middle-of-a-word
    return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix
    
def line_is_section(l):
    return(len(l)>0 and l[0]=="#")
    
def line_is_url(l):
    return(re.match('^http',l))
    
def write_section(s,outFile):
    file = open(outFile,"a",encoding="utf-8") 
    file.write(s + "\n")
    file.close()


def get_url_aggressively(url,retries):
    tries = 0
    while(tries < retries):
        response1 = requests.get(url)
        if(response1.status_code == requests.codes.ok):
            return(response1)
        time.sleep(0.1)
        tries = tries + 1
        
def get_parsed_post(url):
    response1 = get_url_aggressively(url,10)
    response1.raise_for_status()
    response1.encoding='utf-8'
    response=response1.text
    return(BeautifulSoup(response,"html.parser"))
    
def extract_post_info(l,soup):
    title=soup.find('meta',attrs={'name':'og:title'})['content']
    trailingSteemit=re.match('(.*) — Steemit',title)
    if(trailingSteemit):
        title =  trailingSteemit.group(1)
    imageUrl=soup.find('meta',attrs={'name':'og:image'})['content']
    #escape any naughty parens
    imageUrl = re.sub(r'\(','%28',imageUrl)
    imageUrl = re.sub(r'\)','%29',imageUrl)
    imageUrl="https://steemitimages.com/200x200/"+imageUrl
    rawDesc=soup.find('meta',attrs={'name':'og:description'})['content']
    postInfo = {'imageUrl':imageUrl,'title':title,'url':l}
    elog = open("extract.d.log.txt","a",encoding="utf-8")
    bigDesc=""
    elog.write(str(soup))
    elog.write("\n\n--\n\n")

    # TODO write some code that guesses if the text is a caption for a leading image
    # Probably by checking for hyperlinks right after images, CC*, and wikimedia commons
    for el in soup.find('div',class_ = "MarkdownViewer").findChildren():
        #elog.write(p.get_text()+"\n\n~~\n\n")
        if(len(el.get_text())>0 and not re.match('^\s+$',el.get_text())):
            bigDesc=" ".join(el.get_text().split())+"\n\n"
        if(len(bigDesc)>300):
            bigDesc = smart_truncate(bigDesc,300)
            break
    postInfo['bigDesc']="\""+bigDesc+"\""
    
    userMatch=re.match('(.*)by\s+(\S+)\Z',rawDesc)
    if(userMatch):
        desc = userMatch.group(1)
        userName = userMatch.group(2)
        postInfo['desc']= desc
        postInfo['userName']= userName
    return(postInfo)

def write_post_info(l,postTemplate,postNum,outFile):
    soup = get_parsed_post(l)
    postInfo = extract_post_info(l,soup)
    if(postNum%2==0):
        postInfo['pullDir']="pull-left"
    else:
        postInfo['pullDir']="pull-right"
    try:        
        with open(postTemplate) as file_:
            template = Template(file_.read())
        ### header and footer [$title]($url) @$userName,$pullDir">($imageUrl)]($url),$bigDesc
        file = open(outFile,"a",encoding="utf-8") 
        file.write(template.render(postInfo=postInfo))
        file.write("\n\n")
        file.close()
    except:
        print(postInfo)

def write_header(headerFile,outFile):
    with open(headerFile) as file_:
        template = Template(file_.read())
    ### header and footer [$title]($url) @$userName,$pullDir">($imageUrl)]($url),$bigDesc
    file = open(outFile,"w",encoding="utf-8") 
    file.write(template.render(postNumber=postsFile))
    file.write("\n\n")
    file.close()

def write_posts(postsFile,postTemplate,outFile):
        postNum=0
        with open(postsFile,encoding="utf-8") as f:  
            for line in f:
                l = line.strip()
                if(line_is_section(l)):
                    write_section(l,outFile)
                elif(line_is_url(l)):
                    print(l)
                    write_post_info(l,postTemplate,postNum,outFile)
                    postNum=postNum+1
                    
def write_footer(footerFile,outFile):
    with open(footerFile) as file_:
        template = Template(file_.read())
    file = open(outFile,"a",encoding="utf-8") 
    file.write(template.render())
    file.write("\n\n")
    file.close()
    
def write_reading_log(headerFile,footerFile,postsFile,postTemplate):
    outFile="article.md"
    write_header(headerFile,outFile)
    write_posts(postsFile,postTemplate,outFile)
    write_footer(footerFile,outFile)

#simple and lightweight argparser
#thanks to https://gist.github.com/dideler/2395703
def getopts(argv):
    opts = {}  # Empty dictionary to store key-value pairs.
    while argv:  # While there are arguments left to parse...
        if argv[0][0] == '-':  # Found a "-name value" pair.
            opts[argv[0]] = argv[1]  # Add key and value to the dictionary.
        argv = argv[1:]  # Reduce the argument list by copying it starting from index 1.
    return opts

#TODO make sure that this fails better in the face of poor input
if __name__ == "__main__":
    myargs = getopts(argv)
    print(myargs)
    headerFile = "header.md" if('-h' not in myargs) else myargs['-h']
    footerFile = "footer.md" if('-f' not in myargs) else myargs['-f']
    postsFile = "wir.md" if('-p' not in myargs) else myargs['-p']
    postTemplate = "singlePostTemplate.txt" if('-t' not in myargs) else myargs['-t']
    write_reading_log(headerFile,footerFile,postsFile,postTemplate)