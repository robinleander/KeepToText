from __future__ import print_function
import sys, glob, os, shutil, zipfile, time, codecs, re

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

from zipfile import ZipFile

class MyHTMLParser(HTMLParser):
    def attrib_matches(self, tag, attrs):
        return [pair for pair in attrs if
                pair[0] == self.attrib and pair[1] == self.attribVal]    

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            if self.attrib_matches(tag, attrs) and not self.nesting:
                self.nesting = 1
            elif self.nesting:
                self.nesting += 1
        elif tag == "br" and self.nesting:
            self.outf.write(os.linesep)

    def handle_endtag(self, tag):
        if tag == self.tag and self.nesting:
            self.nesting -= 1
            
    def handle_data(self, data):
        if self.nesting:
            self.outf.write(data.strip())
    
    def __init__(self, outf, tag, attrib, attribVal):
        HTMLParser.__init__(self)
        self.outf = outf
        self.tag = tag
        self.attrib = attrib
        self.attribVal = attribVal
        self.nesting = 0
        
def msg(s):
    print(s, file=sys.stderr)
    sys.stderr.flush()
    
def err(s):
    msg(s)
    sys.exit(1)

def htmlFileToText(inputPath, outputDir, tag, attrib, attribVal):
    basename = os.path.basename(inputPath).replace(".html", ".txt")
    outfname = os.path.join(outputDir, basename)
    with codecs.open(inputPath, "r", "utf-8") as inf, codecs.open(outfname, "w", "utf-8") as outf:
        html = inf.read()
        parser = MyHTMLParser(outf, tag, attrib, attribVal)
        parser.feed(html)
        
def htmlDirToText(inputDir, outputDir, tag, attrib, attribVal):
    try_rmtree(outputDir)
    try_mkdir(outputDir)
    msg("Building text files in {0} ...".format(outputDir))
    
    for path in glob.glob(os.path.join(inputDir, "*.html")):
        htmlFileToText(path, outputDir, tag, attrib, attribVal)
        
    msg("Done.")
    
def tryUntilDone(action, check):
    ex = None
    i = 1
    while True:
        try:
            if check(): return
        except Exception as e:
            ex = e
                
        if i == 20: break
        
        try:
            action()
        except Exception as e:
            ex = e
            
        time.sleep(1)
        i += 1
        
    sys.exit(ex if ex != None else "Failed")          
        
def try_rmtree(dir):
    if os.path.isdir(dir): msg("Removing {0}".format(dir))

    def act(): shutil.rmtree(dir)        
    def check(): return not os.path.isdir(dir)        
    tryUntilDone(act, check)
        
def try_mkdir(dir):
    def act(): os.mkdir(dir)        
    def check(): return os.path.isdir(dir)        
    tryUntilDone(act, check)

htmlExt = re.compile(r"\.html$", re.I)

def getHtmlDir(takeoutDir):
    dirs = [os.path.join(takeoutDir, s) for s in os.listdir(takeoutDir)]
    for dir in dirs:
        if not os.path.isdir(dir): continue
        htmlFiles = [f for f in os.listdir(dir) if htmlExt.search(f)]
        if len(htmlFiles) > 0: return dir
            
def keepZipToText(zipFileName):
    zipFileDir = os.path.dirname(zipFileName)
    takeoutDir = os.path.join(zipFileDir, "Takeout")
    outputDir=os.path.join(zipFileDir, "Text")
    
    try_rmtree(takeoutDir)
    
    if os.path.isfile(zipFileName):
        msg("Extracting {0} ...".format(zipFileName))

    try:
        with ZipFile(zipFileName) as zipFile:
            zipFile.extractall(zipFileDir)
    except IOError as e:
        sys.exit(e)

    htmlDir = getHtmlDir(takeoutDir)
    
    if htmlDir is None: err("No Keep directory found")
    
    msg("Keep dir: " + htmlDir)

    htmlDirToText(inputDir=htmlDir, outputDir=outputDir,
        tag="div", attrib="class", attribVal="content")

def main():
    try:
        cmd, zipFile = sys.argv
    except ValueError:
        sys.exit("Usage: {0} zipFile".format(sys.argv[0]))
    
    try:
        keepZipToText(zipFile)
    except WindowsError as e:
        sys.exit(e)

if __name__ == "__main__":
    main()
