from __future__ import print_function
import sys, glob, os, shutil, zipfile, time, codecs, re

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

from zipfile import ZipFile
from lxml import etree
from mako.template import Template
from dateutil.parser import parse,parserinfo


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
        
def msg(s):
    print(s, file=sys.stderr)
    sys.stderr.flush()
    
def err(s):
    msg(s)
    sys.exit(1)

class Note:
    def __init__(self, heading, text, labels):

        self.ctime = parse(heading, parserinfo(dayfirst=True))
        self.text = text
        self.labels = labels

    def getWsSeparatedLabelString(self):
        "Return a WS-separated label string suited for import into CintaNotes"
        labels = []
        for label in self.labels:
            label = label.replace(" ", "_")
            label = label.replace(",", "")
            labels.append(label)
        return " ".join(labels)
        
def extractNoteFromHtmlFile(inputPath):
    """
    Extracts the note heading (containing the ctime), text, and labels from
    an exported Keep HTML file
    """

    with codecs.open(inputPath, 'r', 'utf-8') as myfile:
        data = myfile.read()

    tree = etree.HTML(data)

    heading = tree.xpath("//div[@class='heading']/text()")[0].strip()
    text = tree.xpath("//div[@class='content']/text()")[0]
    labels = tree.xpath("//div[@class='labels']/span[@class='label']/text()")

    return Note(heading, text, labels)
        
def processHtmlFiles(inputDir):
    "Iterates over Keep HTML files to extract relevant notes data"

    msg("Processing HTML files in {}".format(inputDir))
    
    notes = []
    for path in glob.glob(os.path.join(inputDir, "*.html")):
        note = extractNoteFromHtmlFile(path)
        notes.append(note)

    msg("Done.")

    return notes
    
def getHtmlDir(takeoutDir):
    "Returns first subdirectory beneath takeoutDir which contains .html files"
    htmlExt = re.compile(r"\.html$", re.I)
    dirs = [os.path.join(takeoutDir, s) for s in os.listdir(takeoutDir)]
    for dir in dirs:
        if not os.path.isdir(dir): continue
        htmlFiles = [f for f in os.listdir(dir) if htmlExt.search(f)]
        if len(htmlFiles) > 0: return dir

def keepZipToXml(zipFileName):
    zipFileDir = os.path.dirname(zipFileName)
    takeoutDir = os.path.join(zipFileDir, "Takeout")
    xmlFile = os.path.join(zipFileDir, "cintanotes.xml")
    
    try_rmtree(takeoutDir)
    
    if os.path.isfile(zipFileName):
        msg("Extracting {0} ...".format(zipFileName))

    try:
        with ZipFile(zipFileName) as zipFile:
            zipFile.extractall(zipFileDir)
    except (IOError, zipfile.BadZipfile) as e:
        sys.exit(e)

    htmlDir = getHtmlDir(takeoutDir)
    if htmlDir is None: err("No Keep directory found")
    
    msg("Keep dir: " + htmlDir)

    notes = processHtmlFiles(inputDir=htmlDir)

    cintaXml = Template("""
        <?xml version="1.0"?>
        <notebook version="4104" uid="">

        %for note in notes:
                <note uid="" created="${note.ctime.strftime("%Y%m%dT%H%M%S")}"
                    source="" link="" remarks=""
                    tags="${note.getWsSeparatedLabelString()}"
                    section="0" plainText="1">
                    <![CDATA[${note.text}]]>
                </note>
        %endfor

        </notebook>
    """)

    msg("Generating CintaNotes XML file: " + xmlFile)

    with codecs.open(xmlFile, 'w', 'utf-8') as outfile:
        outfile.write(cintaXml.render(notes=notes))


def main():
    try:
        cmd, zipFile = sys.argv
    except ValueError:
        sys.exit("Usage: {0} zipFile".format(sys.argv[0]))
    
    try:
        keepZipToXml(zipFile)
    except WindowsError as e:
        sys.exit(e)

if __name__ == "__main__":
    main()

