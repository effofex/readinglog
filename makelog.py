from jinja2 import Template  # Mapping post info into a readinglog
import os.path               # File manipulation
import json
import markdown
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

def extract_post_info(l):
    # Instead of reading raw html from steemit, I will migrate to RPC calls
    # It will be shoehorned in here and slowly take over during development
    # For my reference (and to give much credit)
    # https://steem.esteem.ws/ is a great reference and way to test calls
    # and https://geo.steem.pl/ is a good automatic way to check rpc nodes
    
    # TODO smart RPC node selection, potentially a pref
    #print(l)
    urlRegMatch = re.search('\/\@(.*)\/(.*)',l)
    payload = {}
    #print(urlRegMatch)
    #print(urlRegMatch.group(1))
    #print(urlRegMatch.group(2))
    if(urlRegMatch):  #TODO exception if not found
        payload['author'] = urlRegMatch.group(1)
        payload['permlink'] = urlRegMatch.group(2)
    #print(payload)
    url = 'https://api.steemjs.com/get_content/'
    response = requests.get(url, params=payload)
    post_json = response.json()
    #print(post_json['author'])
    #print(post_json['permlink'])
    jm = json.loads(post_json['json_metadata'])
    # print(jm['image'][0])
    html_body = markdown.markdown(post_json['body'], output_format='html5')
    # print(html_body)
    newsoup = BeautifulSoup(html_body,"html.parser")
    #print(newsoup.get_text())
    title = post_json['title']
    try:
        imageUrl = jm['image'][0]
    except:
        print("Could not find image in json metadata")
        # TODO for now, just use a blank image, real fix is to try and get it from post
        imageUrl = ''
    # TODO make htis more robust and intentional with urllib.parse and urlib.quote
    #escape any naughty parens
    imageUrl = re.sub(r'\(','%28',imageUrl)
    imageUrl = re.sub(r'\)','%29',imageUrl)
    imageUrl="http://steemitimages.com/200x200/"+imageUrl
    # TODO, allow user to specify busy/steemit/etc as domain for url and use pst_json['url'] for the path
    postInfo = {'imageUrl':imageUrl,'title':title,'url':l}
    article_text = newsoup.get_text()
    article_text = re.sub('\(?https?://.*[jpg|gif|png|jpeg|tiff|tif]\)?','',article_text)
    postInfo['bigDesc']="\""+smart_truncate(article_text,length=256).strip()+"\""
    postInfo['desc']= smart_truncate(newsoup.get_text(),length=100)
    postInfo['userName']= post_json['author']
    #print(postInfo)
    return(postInfo)

def write_post_info(l,postTemplate,postNum,outFile):
    postInfo = extract_post_info(l)
    if(postNum%2==0):
        postInfo['pullDir']="pull-left"
    else:
        postInfo['pullDir']="pull-right"
    try:        
        with open(postTemplate) as file_:
            template = Template(file_.read())
        file = open(outFile,"a",encoding="utf-8") 
        file.write(template.render(postInfo=postInfo))
        file.write("\n\n")
        file.close()
    except Exception as e:
        print(e)
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
