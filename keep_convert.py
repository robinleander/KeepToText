#!/usr/bin/env python2.7

from __future__ import print_function

import argparse
import glob
import os
import sys
import base64
import binascii
import re
import time

from dateutil.parser import parse, parserinfo
from datetime import datetime
import hashlib


def msg(s, *args, **kwargs):
    print(s, *args, file=sys.stderr, **kwargs)
    sys.stderr.flush()


def hash_all(all, fn=hashlib.sha384):
    rv = fn()
    for one in all:
        if one is not None:
            if hasattr(one, 'hash'):
                rv.update(one.hash())
            else:
                rv.update(fn(one).hexdigest())
        else:
            rv.update('')
    return rv.hexdigest()


class Note:
    def __init__(self, ctime, title, text, labels, attachments):
        self.ctime = parse(ctime, parserinfo(dayfirst=True))
        self.title = title if title != ctime else None
        self.text = text
        self.labels = labels
        self.attachments = attachments

    def get_ws_label_string(self):
        """Return a WS-separated label string suited for import into CintaNotes"""
        labels = []
        for label in self.labels:
            label = label.replace(" ", "_")
            label = label.replace(",", "")
            labels.append(label)
        return " ".join(labels)

    def __str__(self):
        return 'CREATED: {}\nTITLE: {}\nLABELS: {}\n\n{}'.format(self.ctime, self.title, self.labels, self.text)

    def hash(self):
        return hash_all([str(self.ctime), self.title, self.text] + self.labels + self.attachments)


class Attachment:
    def __init__(self, src):
        src = str(src)
        match = re.match(r'^data:([^;]*);base64,(.*)$', src)
        if match:
            self.mime = match.group(1)
            self.data = base64.b64decode(match.group(2))
        else:
            self.data = src

    def hash(self):
        return hash_all([self.mime, self.data])


def get_note(filename):
    """
    Extracts the note heading (containing the ctime), text, and labels from
    an exported Keep HTML file
    """

    with open(filename, 'r') as f:
        data = f.read()

    from lxml import etree
    tree = etree.HTML(data)

    title = tree.xpath(".//title/text()")[0].strip()
    ctime = tree.xpath(".//div[@class='heading']/text()")[0].strip()
    text = '\n'.join(tree.xpath(".//div[@class='content']/text()"))
    labels = tree.xpath(".//div[@class='labels']/span[@class='label']/text()")
    attachments = tree.xpath(".//div[@class='attachments']//img/@src")
    attachments = map(lambda x: Attachment(x), attachments)

    return Note(ctime, title, text, labels, attachments)


def export_takeout(dir, exporter):
    """Iterates over Keep HTML files to extract relevant notes data"""

    msg('Processing notes in {}'.format(dir))

    for path in glob.glob(os.path.join(dir, "*")):
        msg('Exporting {}'.format(path))
        if path.endswith('.html'):
            exporter.export(get_note(path))
        else:
            # TODO: implement
            msg('Skipping since not a .html file.')
    exporter.finalize()
    msg("Done.")


LOGFILE = 'notes.log'


class APIClient:
    def __init__(self, auth_token, sandbox, china, **kwargs):
        if not auth_token:
            msg('Auth Token required')
            exit(1)
        self.auth_token_hash = hashlib.sha384(auth_token).hexdigest()
        import evernote.edam.userstore.constants as UserStoreConstants
        from evernote.api.client import EvernoteClient
        self.client = EvernoteClient(token=auth_token, sandbox=sandbox, china=china)
        user_store = self.client.get_user_store()

        version_ok = user_store.checkVersion(
            'GKeep Import',
            UserStoreConstants.EDAM_VERSION_MAJOR,
            UserStoreConstants.EDAM_VERSION_MINOR
        )
        if not version_ok:
            msg('Evernote API version is not OK!')
            exit(1)

        self.note_store = self.client.get_note_store()
        try:
            self.log = []
            with open(LOGFILE, 'r') as f:
                self.log = filter(lambda x: len(x) > 0 and x[0] != '#', map(lambda x: x.split(), f.read().splitlines()))
        except IOError:
            with open(LOGFILE, 'w') as f:
                f.write('# This file contains a log of the transactions done with the server.\n')
                f.write('# This allows the client to remember which notes have already been uploaded.\n')
                f.write('# You can delete this file if you want to upload the same notes to the same account again.\n')
                f.write('\n')

    def export(self, note):
        if ['CREATE', self.auth_token_hash, note.hash()] in self.log:
            msg('Skipping since note has already been created (Delete {} to force creation).'.format(LOGFILE))
            return
        import evernote.edam.type.ttypes as Types

        # To create a new note, simply create a new Note object and fill in
        # attributes such as the note's title.
        enote = Types.Note()
        enote.created = int(time.mktime(note.ctime.timetuple()))
        enote.title = note.title or 'Untitled'

        # The content of an Evernote note is represented using Evernote Markup Language
        # (ENML). The full ENML specification can be found in the Evernote API Overview
        # at http://dev.evernote.com/documentation/cloud/chapters/ENML.php
        from xml.sax.saxutils import escape
        enote.content = '<?xml version="1.0" encoding="utf-8"?>' + \
                        '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">' + \
                        '<en-note>' + \
                        escape(note.text).replace('\n', '<br/>').encode('utf-8')
        enote.resources = []
        for attachment in note.attachments:
            data = Types.Data()
            data.size = len(attachment.data)
            data.bodyHash = hashlib.md5(attachment.data).digest()
            data.body = attachment.data

            resource = Types.Resource()
            mime = attachment.mime or 'image/png'
            resource.mime = mime
            resource.data = data
            enote.resources.append(resource)
            enote.content += '<en-media type="' + mime + '" hash="' + binascii.hexlify(data.bodyHash) + '"/>'
        enote.content += '</en-note>'
        enote.tagNames = note.labels

        # Finally, send the new note to Evernote using the createNote method
        # The new Note object that is returned will contain server-generated
        # attributes such as the new note's unique GUID.
        self.note_store.createNote(enote)
        with open(LOGFILE, 'a') as f:
            f.write('# created note at {}\n'.format(datetime.now().isoformat(' ')))
            f.write('CREATE {} {}\n'.format(self.auth_token_hash, note.hash()))

    def finalize(self):
        pass


class CintaXML:
    def __init__(self, output_filename, **kwargs):
        if not output_filename:
            msg('Ouput filename required')
            exit(1)
        self.notes = []
        self.output_filename = output_filename

    def finalize(self):
        from mako.template import Template
        cinta_xml = Template("""
            <?xml version="1.0"?>
            <notebook version="4104" uid="">

            %for note in notes:
                    <note uid="" created="${note.ctime.strftime("%Y%m%dT%H%M%S")}"
                        source="" link="" remarks=""
                        tags="${note.get_ws_label_string()}"
                        section="0" plainText="1">
                        <![CDATA[${note.text}]]>
                    </note>
            %endfor

            </notebook>
        """)

        with open(self.output_filename, 'w') as f:
            f.write(cinta_xml.render(notes=self.notes))

    def export(self, note):
        self.notes.append(note)


class Simulate:
    def __init__(self, **kwargs):
        pass

    def export(self, note):
        msg(note)

    def finalize(self):
        pass


def main():
    exporters = {
        'EvernoteAPI': APIClient,
        'CintaNotes': CintaXML,
        'Simulate': Simulate,
    }
    parser = argparse.ArgumentParser()
    parser.add_argument('TAKEOUT', help='Keep\'s Takeout directory')
    parser.add_argument('--exporter', choices=exporters.keys(), default='EvernoteAPI', help='Notes exporter')

    group = parser.add_argument_group('Evernote API exporter options')
    group.add_argument('--auth-token', help='Auth Token to use')
    group.add_argument('--sandbox', action='store_true', help='Use the sandbox servers')
    group.add_argument('--china', action='store_true', help='Use evernote china')

    group = parser.add_argument_group('Cinta exporter options')
    group.add_argument('--outfile', help='Output file')

    args = parser.parse_args()

    exporter = exporters[args.exporter](
        auth_token=args.auth_token,
        sandbox=args.sandbox,
        china=args.china,
        output_filename=args.outfile,
    )
    export_takeout(args.TAKEOUT, exporter)


if __name__ == "__main__":
    if reload is not None:
        reload(sys)
        sys.setdefaultencoding('utf8')
    main()
